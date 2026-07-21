import time
import json

from storytoolkitai import USER_DATA_PATH
from storytoolkitai.core.logger import *
from storytoolkitai.core.events import (
    EngineEvent,
    EventEmitter,
    create_action_triggered_event,
)

import torch
from threading import Thread


QUEUE_FILE_PATH = os.path.join(USER_DATA_PATH, 'queue.json')


class ProcessingQueue:
    """
    This class handles the processing queue:
    """

    def __init__(
        self,
        task_handlers=None,
        event_emitter=None,
    ):
        # the queue only needs the task names and their callables
        # it must not keep a reference to the complete ToolkitOps object
        self.task_handlers = (
            task_handlers
            if isinstance(task_handlers, dict)
            else {}
        )

        # ToolkitOps passes its shared emitter here
        # standalone queue instances, such as isolated tests,
        # receive their own emitter by default
        self.events = (
            event_emitter
            if event_emitter is not None
            else EventEmitter()
        )

        # ToolkitOps passes its shared emitter here
        # standalone queue instances, such as isolated tests,
        # receive their own emitter by default
        self.events = (
            event_emitter
            if event_emitter is not None
            else EventEmitter()
        )

        # this holds the queue ids of the items that need to be processed next
        # once the item is sent for processing, it is removed from this list and only remains in the queue history
        # since it's an ordered list, the first item in the list is the next item to be processed
        self.queue = []

        # this holds the queue history
        # - when an object is added to the queue it must also have a corresponding entry in the queue history
        # - we are only tracking the status of the object in the queue history
        # - when an object sent for processing it will remain in the history so that we can track its status
        self.queue_history = []

        # this keeps track of the threads that are processing the queue by device
        # the key is the device name and the value is a dict with the queue id and the thread object
        # for eg. {'cuda:0': {'queue_id': queue_id, 'thread': <Thread(Thread-1, started 1234567890123)>}, ...}
        self.queue_threads = {}

        # this holds other variables that don't need to be part of the queue history,
        # but can be shared between threads
        # the key is the queue id and the value is a dict variable names and values
        self.queue_variables = {}

        # how much to wait until checking if there are items in the queue that can be processed
        # disabled for now - if we activate this we need to make sure that the device is not used by another thread
        # by checking the queue_threads dict
        # self.queue_check_interval = 30 # seconds

    def _emit_job_changed(self, item):
        """
        Publish a stable summary after a queue item changes.

        Queue items may contain Python callables and temporary processing
        objects. Those implementation details must not be placed in events.
        """

        if not isinstance(item, dict):
            return False

        self.events.emit(
            EngineEvent(
                type='job.changed',
                data={
                    'job_id': item.get('queue_id'),
                    'status': item.get('status'),
                    'progress': item.get('progress'),
                    'item_type': item.get('item_type'),
                },
            )
        )

        return True

    def _emit_legacy_action(self, action):
        """
        Publish a remaining legacy action through the event emitter.

        This is temporarily kept for the advanced-search stop callback.
        Search-specific action names will be removed when search ownership
        moves behind StoryToolkitEngine in Step 9.
        """

        if not action:
            return False

        self.events.emit(
            create_action_triggered_event(
                action=action,
            )
        )

        return True

    def generate_queue_id(self, name: str = None) -> str:
        """
        This function generates a queue id for a task
        """

        # keep generating a queue id until it's not similar to one that already exists in the queue history
        while True:

            # use the name if one was provided
            # and a timestamp to make it as unique as possible
            queue_id = "{}{}".format(
                ((name.replace(' ', '') + '-') if name else ''),
                time.time(),
            )

            # if the queue id doesn't return an item
            if not self.get_item(queue_id=queue_id):

                queue_item = {
                    'queue_id': queue_id,
                    'name': '',
                    'status': 'pending',
                }

                logger.debug(
                    'Added queue id {} to queue history'.format(queue_id)
                )

                # publish the pending item through the engine event stream
                self._emit_job_changed(queue_item)

                return queue_id

    def add_to_queue(self,
                     tasks: list or str = None,
                     queue_id: str = None,
                     item_type: str = None,
                     source_file_path=None,
                     task_data=None,
                     device=None,
                     required_device_type=None,
                     ping=True,
                     **kwargs
                     ) -> str or bool:
        """
        This function adds a task to the processing queue
        It either needs a source_file_path (audio, video etc.)
        or directly the task_data (transcription, search corpus etc.)

        Once it adds the task, it also pings the queue manager to start processing the queue
        (if it is not already running)

        :param tasks: a list of tasks to be added to the queue, or a single task
            (don't confuse with the task queue, which will be determined by the task dispatcher based on this list)

        :param queue_id: the queue id of the task - if None, one will be generated

        :param item_type: the main type of item that is being processed
                     - this could be used for UI purposes on the Queue window
                     - this is included in queue events so callers know what kind of item changed

        :param source_file_path: the path(s) to the source file(s) - if empty, we need to have the task_data

        :param task_data: the task data (transcription, search corpus etc.) - if empty, we need a source_file_path

        :param device: the device to use for processing the task, if empty,
                        we will use the next available device suitable for the task (device_required must be passed)

        :param required_device_type: the device type required for processing the task (cpu, cuda, etc.)

        :param ping: whether to ping the queue manager to start processing the queue

        :param kwargs: any other key-value pairs to be added to the queue item

        :return: the queue id of the task or False if something went wrong

        """

        # if the queue id is not passed, generate one
        if not queue_id:
            queue_id = self.generate_queue_id(name=kwargs.get('name', None))

        # check if we have task queue (a list of functions to be executed) via the task dispatcher
        task_queue = self.task_dispatcher(tasks=tasks)

        # if we don't have a task queue, abort
        if not task_queue:
            logger.error('Empty task queue - could not add item {} to queue'.format(queue_id))
            return False

        # add the type
        kwargs['item_type'] = item_type

        # if we have a task queue, add it to the kwargs
        kwargs['task_queue'] = task_queue

        # also add the tasks for future reference
        kwargs['tasks'] = tasks

        # if we don't have source files nor task data, abort
        if not source_file_path and not task_data:
            logger.error('Invalid task (no source files or data) - could not add item {} to queue'
                         .format(queue_id))
            return False

        # add the queue_id to the kwargs
        kwargs['queue_id'] = queue_id

        # if we have a source file path, add it to the kwargs
        if source_file_path:
            kwargs['source_file_path'] = source_file_path

        # if we have task data, add it to the kwargs
        if task_data:
            kwargs['task_data'] = task_data

        # if we have a device, add it to the kwargs
        if device is None:
            logger.error('Device must be specified when adding an item to the queue')
            return False

        # make sure we have a string as a device, and not a torch.device object
        if isinstance(device, torch.device):
            device = str(device.type)

        kwargs['device'] = device

        # if we have a required device type, add it to the kwargs
        if required_device_type:
            kwargs['required_device_type'] = required_device_type

        # add the 'queued' status to the kwargs
        kwargs['status'] = 'queued'

        # check if the queue id already exists in the queue history
        item = self.get_item(queue_id=queue_id)
        if not item:

            # add the kwargs to the queue history
            self.queue_history.append(kwargs)

            logger.debug(
                'Added item {} to queue history'.format(
                    queue_id
                )
            )

            # publish the new queue item through the engine event stream
            self._emit_job_changed(kwargs)

        else:
            # just update the item, but make sure that the queue id is not stripped
            kwargs['queue_id'] = queue_id
            self.update_queue_item(**kwargs)

        # add the queue id to the queue
        self.queue.append(queue_id)

        logger.debug('Added item {} to queue'.format(queue_id))

        # ping the queue to start processing
        if ping:
            self.ping_queue()

        # save the queue to a file
        self.save_queue_to_file()

        # throttle for a bit to avoid queue id queue id collisions,
        # if this is a batch
        time.sleep(0.01)

        # return the queue id if we reached this point
        return queue_id

    def add_dependency(self, queue_id, dependency_id=None):
        """
        This adds the dependency_id to the list of dependencies of the queue_id
        """

        # get the item
        item = self.get_item(queue_id)

        # if the item doesn't exist, abort
        if not item:
            logger.error('Unable to add dependency - queue id {} not found in queue history'.format(queue_id))
            return False

        # if the item exists, add the dependency_id to the list of dependencies
        if dependency_id:

            if 'dependencies' not in item:
                item['dependencies'] = []

            item['dependencies'].append(dependency_id)

        # update the item
        self.update_queue_item(**item)

        # return the item
        return item

    def pass_dependency_data(self, queue_id, dependency_id, override=False, save_to_file=False, only_done=True):
        """
        This passes all the data from the item with the dependency_id to the item with the queue_id
        (all except the queue_id and name)

        This will not overwrite any existing data in the item with the queue_id, unless override is set to True
        """

        # the stuff that we're never supposed to override
        override_not_allowed = ['queue_id', 'name', 'tasks', 'device', 'task_queue', 'dependencies']

        # get the item
        item = self.get_item(queue_id)

        # if the item doesn't exist, abort
        if not item:
            logger.error('Unable to pass dependency data - queue id {} not found in queue history'.format(queue_id))
            return False

        # get the dependency item
        dependency_item = self.get_item(dependency_id)

        # if the dependency item doesn't exist, abort
        if not dependency_item:
            logger.error('Unable to pass dependency data - dependency id {} not found in queue history'
                         .format(dependency_id))
            return False

        # if only_done is set to True, check if the dependency item is done
        if only_done and 'status' in dependency_item and dependency_item['status'] != 'done':
            logger.error('Unable to pass dependency data - dependency id {} is not done'.format(dependency_id))
            return False

        # if the dependency item exists, pass all the data from the dependency item to the item
        # except the queue-related data above
        for key, value in dependency_item.items():

            # we will use the override_not_allowed list to make sure we don't override stuff
            # also, we will only override if override is set to True
            if (override or key not in item) and key not in override_not_allowed:
                # pass the key-value pair to the item
                item[key] = value

        # update the item
        self.update_queue_item(**item, save_to_file=save_to_file)

    def update_queue_item(self, queue_id, save_to_file=True, **kwargs):
        """
        This function updates a queue item in the queue history

        :param queue_id: the queue id of the queue item to be updated
        :param save_to_file: whether to save the queue to a file after updating the item
        :param kwargs: the key-value pairs to be updated

        :return: the updated queue item or False if something went wrong
        """

        # get the full item and make sure you don't strip the queue id
        item = self.get_item(queue_id)

        if not item:
            logger.error('Unable to update queue item - queue id {} not found in queue history'.format(queue_id))
            return False

        # update the item
        new_item = item

        # keep all the existing keys and values, but update the ones that are passed in kwargs
        for key, value in kwargs.items():
            new_item[key] = value

        # make sure to always pass the queue id too
        new_item['queue_id'] = queue_id

        # add the last_update timestamp
        new_item['last_update'] = time.time()

        # find the item index in the queue history according to its queue id
        for index, item in enumerate(self.queue_history):

            if 'queue_id' in item and item['queue_id'] == queue_id:
                item_index = index

                # replace the item in the queue history
                self.queue_history[item_index] = new_item

                # publish a stable summary of the changed queue item
                self._emit_job_changed(new_item)

                # save the queue to a file
                if save_to_file:
                    self.save_queue_to_file()

                # and return the updated item
                return new_item

        # let's hope this doesn't happen...
        return False

    def reorder_queue(self, new_queue_order) -> bool:
        """
        This function takes the new queue order and re-orders the queue and the queue history accordingly,
        but does not add items that are not in the queue

        :param new_queue_order: the new queue order
        :return:
        """

        # return False if the new queue order is not a list
        if not isinstance(new_queue_order, list):
            logger.error('Unable to reorder queue - new queue order is not a list')
            return False

        # first, reorder the QUEUE (then the queue history)

        # start by removing all the items that are not in the queue
        new_queue_order = [item for item in new_queue_order if item in self.queue]

        # now check that the new queue is the same length as the old queue
        if len(new_queue_order) != len(self.queue):
            logger.error('Unable to reorder queue - new queue order is not the same length as the queue')
            return False

        # but if the queues are empty, just return True
        if not new_queue_order and not self.queue:
            logger.debug("Queue is empty, nothing to reorder.")
            return True

        # re-order the queue
        self.queue = new_queue_order

        # now re-order the QUEUE HISTORY

        # organize all the items that have the status 'processing', 'done', or 'failed' in a list
        # these items will stay at the beginning of the queue history
        # with their original order since they're finished
        processed_items = [item for item in self.queue_history
                           if 'queue_id' in item
                           and 'status' in item
                           and item['status'] in ['processing', 'done', 'failed', 'canceled', 'canceling']
                           ]

        # extract queue_ids of processed items
        processed_ids = [item['queue_id'] for item in processed_items]

        # remove any processed items from the new_queue_order list by the 'queue_id' key in processed_items
        new_queue_order = [item for item in new_queue_order if item['queue_id'] not in processed_ids]

        # now create a list of dictionaries with the remaining items in the new_queue_order
        # - keep their entire dictionary structure from the queue history
        # - but use the order in the new_queue_order list

        # start the remaining items list with the processed items
        queue_history = processed_items
        for item in new_queue_order:

            # get the item from the queue history
            queue_item = self.get_item(queue_id=item['queue_id'])

            # if the item is not in the queue history, skip it
            if queue_item is None:
                continue

            # add the item to the remaining items list
            queue_history.append(queue_item)

        # now replace the queue history with the remaining items list
        self.queue_history = queue_history

        return True

    def cancel_item(self, queue_id: str):
        """
        This function removes a task from the queue of items to be processed

        And updates the status in the queue history to 'canceled'
        """

        if queue_id is None:
            logger.error('Unable to cancel item - queue id is None')
            return False

        # remove the item from the queue
        # (to avoid processing it if it's not already being processed)
        if queue_id in self.queue:
            self.queue.remove(queue_id)

        # try to get the item from the queue history
        item = self.get_item(queue_id)

        if not item:
            logger.warning('Unable to cancel item - queue id {} not found in queue history'.format(queue_id))
            return None

        # if the current status is 'done' or 'failed',
        # it doesn't make sense to cancel it
        if item['status'] in ['done', 'failed']:
            logger.debug('Item {} is already done or failed, cannot cancel.'
                         .format(queue_id))

        # check if the item is currently processing in the thread pool
        # if it is, set the status to 'canceling', since we can't remove it from the thread pool

        # go through all the threads in queue_threads
        for thread in self.queue_threads:

            if isinstance(thread, dict) \
                    and 'queue_id' in thread \
                    and thread['queue_id'] == queue_id:

                self._notify_on_stop_action(item=item)

                # set the status to 'canceling' in the queue history
                # and hope that someone will be watching the status and cancel the item!
                return self.update_queue_item(queue_id=queue_id, status='canceled')

        # if we reached this point,
        # the item is not currently being processed,
        # so we can remove it from the queue history
        self._notify_on_stop_action(item=item)
        return self.update_queue_item(queue_id=queue_id, status='canceled')

    def cancel_if_canceled(self, queue_id):
        """
        Checks if the queue item has been canceled and cancels it if it has
        This usually happens if a process sends a 'canceled' status
        so that item is canceled when the current task is finished

        :param queue_id: the queue id of the item to check
        :return True if the item was canceled, False if not, None if the passed queue id is None
        """

        if queue_id is None:
            logger.debug('Unable to cancel item - queue id is None')
            return None

        queue_item = self.get_item(queue_id=queue_id)

        # if the status is 'canceling' or 'canceled', cancel the item
        if queue_item \
                and isinstance(queue_item, dict) \
                and 'status' in queue_item \
                and queue_item['status'] in ['canceling', 'canceled']:
            # cancel the item
            self.cancel_item(queue_id=queue_id)

            # the item was canceled
            return True

        # the item was not canceled
        return False

    def set_to_canceled(self, queue_id):
        """
        Request safe cancellation of a queue item.

        Items that have not started can be canceled immediately. Items that
        are currently running are marked as ``canceling`` so the active task
        can finish before the queue stops the remaining tasks.

        :param queue_id: the queue id of the item to cancel
        :return: True if cancellation was requested, False otherwise
        """

        # get the item from the queue history
        item = self.get_item(queue_id=queue_id)
        if not item or not isinstance(item, dict):
            logger.warning(
                'Unable to set item to canceled - queue id {} not found '
                'in queue history'.format(queue_id)
            )
            return False

        # finished or already canceled items cannot be canceled again
        if item.get('status') in ['done', 'failed', 'canceled']:
            logger.debug(
                'Item {} is already finished or canceled, cannot cancel.'
                .format(queue_id)
            )
            return False

        # a canceling item may still be finishing its current task
        if item.get('status') == 'canceling':

            # finalize the cancellation once the item has left the thread pool
            if not self.is_item_in_thread(queue_id=queue_id):
                return bool(self.cancel_item(queue_id=queue_id))

            return True

        # items that have not started can be removed from the runnable queue
        # and marked as canceled immediately
        if not self.is_item_in_thread(queue_id=queue_id):
            return bool(self.cancel_item(queue_id=queue_id))

        # running items must finish their current task before cancellation
        return bool(
            self.update_queue_item(
                queue_id=queue_id,
                status='canceling',
                progress='',
            )
        )

    def get_item(self, queue_id: str) -> dict or None:
        """
        This function checks if a queue id is in the queue history and returns the item if it is
        :param queue_id: the queue id to check
        :return: the item if it is in the queue history, None otherwise
        """

        found_item = None

        if queue_id is None:
            return None

        # the queue history is a list of dictionaries, so we need to iterate through it to find the item
        for item in self.queue_history:

            # if we found the item by its queue id, use it and break the loop
            if 'queue_id' in item and item['queue_id'] == queue_id:
                found_item = item
                break

        return found_item

    def get_status(self, queue_id: str) -> str or None:
        """
        This function checks if a queue id is in the queue history and returns the status if it is
        :param queue_id: the queue id to check
        :return: the status if it is in the queue history, None otherwise
        """

        item = self.get_item(queue_id=queue_id)

        if item and isinstance(item, dict) and 'status' in item:
            return item['status']

        return None

    def get_progress(self, queue_id: str) -> str or None:
        """
        This function returns the 'progress' of a queue item,
        0 if it has no progress or None if the item doesn't exist
        """

        item = self.get_item(queue_id=queue_id)

        if not item:
            return None

        if isinstance(item, dict) and 'progress' in item:
            return item['progress']

        else:
            return '0'

    def get_all_queue_items(self, status: str or list or None = None, not_status: str or list or None = None) \
            -> dict:
        """
        This function returns all the items in the queue history in an dict,
        where the queue id is the key and the value is the item
        """

        # if the status is a string, convert it to a list
        if isinstance(status, str):
            status = [status]

        # if the not_status is a string, convert it to a list
        if isinstance(not_status, str):
            not_status = [not_status]

        all_queue_items = {}

        for item in self.queue_history:

            # if the status is not None check if the item has the status we are looking for
            # and if not, skip it
            if status is not None \
                    and 'status' in item and item['status'] not in status:
                continue

            # if the not_status is not None check if the item has the status we don't want
            # and if it does, skip it
            if not_status is not None \
                    and 'status' in item and item['status'] in not_status:
                continue

            all_queue_items[item['queue_id']] = item

        return all_queue_items

    def task_dispatcher(self, tasks: list or str) -> list or bool:
        """
        Convert task names into the functions that execute those tasks.

        The task-handler dictionary is supplied when the queue is created.
        This keeps ProcessingQueue independent from ToolkitOps.

        :param tasks: task names to dispatch, or a single task name
        :return: ordered task functions, or False if none were found
        """

        task_queue = []

        # no task names means there is nothing to dispatch
        if tasks is None:
            logger.warning(
                'Unable to dispatch tasks - no tasks were specified'
            )
            return False

        # handle one task name in the same way as a list of task names
        if isinstance(tasks, str):
            tasks = [tasks]

        for task in tasks:

            # skip unknown task names but continue checking the others
            if task not in self.task_handlers:
                logger.warning(
                    'Unable to dispatch task {} - '
                    'task not in task handlers'.format(task)
                )
                continue

            handlers = self.task_handlers[task]

            if not isinstance(handlers, list) or not handlers:
                logger.error(
                    'Unable to dispatch task {} - '
                    'task handler list is empty'.format(task)
                )
                continue

            task_queue.extend(handlers)

        if not task_queue:
            return False

        return task_queue

    def _notify_on_stop_action(self, item):
        """
        Publish the temporary search-specific action for a stopped job.

        The advanced-search workflow still identifies its failure callback
        through on_stop_action_name, but we will replace this with search
        events containing normal job and search identifiers.
        """

        if (
            isinstance(item, dict)
            and item.get('on_stop_action_name')
        ):
            self._emit_legacy_action(
                item['on_stop_action_name']
            )

    def execute_item_tasks(self, queue_id, task_queue: list, **kwargs):
        """
        This function executes the functions in the task queue for a given queue item
        """

        # cancel item if someone or something requested it
        if self.cancel_if_canceled(queue_id=queue_id):
            return False

        if task_queue is None:
            logger.error('Unable to execute tasks for item {} - no tasks were specified'.format(queue_id))
            return False

        # keep track of the device we're using
        device = kwargs.get('device', None)

        # get the item details from the queue history
        item = self.get_item(queue_id=queue_id)

        # if the item has dependencies, pass_dependency_data for all of them
        if 'dependencies' in item:
            for dependency_id in item['dependencies']:
                self.pass_dependency_data(queue_id=queue_id, dependency_id=dependency_id,
                                          override=True, save_to_file=False)

        executed = False

        # take each task in the list of tasks
        for task in task_queue:

            # stop if the item cannot be found anymore - that would be strange
            if item is None:
                logger.error('Unable to execute task {} for item {} - item not found in queue history'
                             .format(task, queue_id))
                return False

            # stop if the item's status is 'canceling'
            # - this means that the user has requested to cancel the item
            if item['status'] == 'canceling':
                self.update_status(queue_id=queue_id, status='canceled')

                # notify on_stop observers
                self._notify_on_stop_action(item=item)

                return False

            # stop also if something set the status to 'failed'
            if item['status'] == 'failed':
                # notify on_stop observers
                self._notify_on_stop_action(item=item)
                return False

            try:

                # update the 'last_task' key in the queue item
                # so we know which task is being executed but also which task failed if the execution fails
                self.update_queue_item(queue_id=queue_id, last_task=task)

                # update the status of the queue item to 'processing'
                # - this should be updated in more detail from within the task itself (if needed)
                self.update_status(queue_id=queue_id, status='processing')

                # get the item one last time to pass it to the task
                item = self.get_item(queue_id=queue_id)

                # only merge if the kwargs is a dictionary
                # (whisper transcribe returns bool or a string right now - we need to fix that)
                kwargs = {**kwargs, **item} if isinstance(kwargs, dict) else item

                # execute the task, but merge the kwargs with the item
                # then re-update the kwargs with the result of the task
                kwargs = task(**{**kwargs, **item})

                logger.debug('Finished execution of {} for queue item {}'.format(task.__name__, queue_id))

                # wait a moment
                time.sleep(0.1)

                # keep task-completion callbacks working until the explicit
                # queue task event is introduced in the next commit
                self._emit_legacy_action(
                    '{}_queue_item_done'.format(
                        item['item_type']
                    )
                )
                self._emit_legacy_action(
                    '{}_queue_item_done'.format(queue_id)
                )

                executed = True

            except:

                logger.error('Unable to execute task {} for queue item {}'.format(task, queue_id), exc_info=True)

                # update the status of the queue item to 'failed'
                self.update_status(queue_id=queue_id, status='failed')

                # notify on_stop observers
                self._notify_on_stop_action(item=item)

                # stop the execution
                executed = False

        # remove the thread from the queue threads to free up the device
        self.remove_thread_from_queue_threads(device=device)

        # then ping the queue again
        self.ping_queue()

        # if we get here, the execution was successful
        return executed

    def update_status(self, queue_id, status, fail_error=None):
        """
        This function updates the status of a queue item
        """

        if queue_id is None:
            return None

        item = self.get_item(queue_id=queue_id)
        if not item:
            logger.error('Unable to update status for queue item {} - item not found'.format(queue_id))
            return False

        item['status'] = status

        if fail_error:
            item['fail_error'] = fail_error

        # also reset the progress if the status update is 'done', 'failed', 'canceled' or 'canceling'
        if status in ['done', 'failed', 'canceled', 'canceling'] and 'progress' in item:
            del item['progress']

        self.update_queue_item(**item)

    def update_output(self, queue_id, output, append=True):
        """
        This function adds output to the queue item
        """

        item = self.get_item(queue_id=queue_id)
        if not item:
            logger.error('Unable to update output for queue item {} - item not found'.format(queue_id))
            return False

        # chose between appending or replacing the output
        if append:
            if 'output' not in item:
                item['output'] = []

            item['output'].append(output)
        else:
            item['output'] = [output]

        # update the queue item, but prevent saving the item to file
        # since the output will not get saved anyway
        self.update_queue_item(save_to_file=False, **item)

    def ping_queue(self):
        """
        Checks if there are items left in the queue and executes the first one if there are
        """

        # if there are no items in the queue, return False
        if len(self.queue) == 0:
            logger.debug('No items left in the queue. Try to ping the queue again later.')
            return False

        # get the first item in the queue
        queue_index = 0
        queue_id = self.queue[queue_index]
        reorder_queue = False

        # try to start the next item from the queue that can be started
        while not (can_start := self._item_can_start(queue_id=queue_id)):

            logger.debug('Item {} cannot start. Trying the next one.'.format(queue_id))

            # if we received a None from _item_can_start,
            # it means that the item doesn't exist anymore relative to when we started the loop
            # so we shouldn't increment the queue index
            if can_start is not None:
                # add +1 to the queue index
                queue_index += 1

            # check if the queue index is out of range
            if queue_index >= len(self.queue):
                # and abort if it is
                if len(self.queue) == 0:
                    logger.debug("Queue is empty.")
                else:
                    logger.debug('None of the queue items are ready to start. Try again later.')
                return False

            # get the next item in the queue
            queue_id = self.queue[queue_index]



        # todo: fix this
        """
        # try to see if we can start this item
        # and loop through the queue until we find one that we can start
        # or until we reach the end of the queue
        # todo: update the item status to failed if we get a None returned from _item_can_start
        while not self._item_can_start(queue_id=queue_id):

            # add +1 to the queue index
            queue_index += 1

            # and try again (if the queue index is out of range, this will return False)
            if queue_index >= len(self.queue):
                logger.debug('Left queue items not ready to start. Try again later.')
                return False

            # get the next item in the queue
            queue_id = self.queue[queue_index]

            # mark that we need to reorder the queue
            reorder_queue = True

        # make sure that we re-order the queue
        if reorder_queue:

            # first get the old order
            # (use a copy of the list to avoid changing the original list due to mutability)
            new_queue_order = [queue_id for queue_id in self.queue]

            # then remove the item from the old order (from whatever position it was in)
            new_queue_order.pop(queue_index)

            # and add it back to the beginning of the list
            new_queue_order.insert(0, queue_id)

            self.reorder_queue(new_queue_order=new_queue_order)
        """

        # get the item details from the queue history
        kwargs = self.get_item(queue_id=queue_id)

        # check if the device is available
        if not self.is_device_available(device=kwargs['device']):
            logger.debug('Device busy. Try again later.')
            return False

        # check all the kwargs and make sure that all their keys are strings
        # otherwise the thread will fail to start
        filtered_kwargs = {}
        for key, value in kwargs.items():

            if isinstance(key, str):
                filtered_kwargs[key] = value

        # create a thread to execute the tasks for this item
        thread = Thread(target=self.execute_item_tasks, kwargs=filtered_kwargs)

        # add the thread to the threads dictionary so that other processes know that the device is busy
        self.add_thread_to_queue_threads(device=kwargs['device'], queue_id=kwargs['queue_id'], thread=thread)

        # start the thread
        thread.start()

        # once the thread has started, we can remove the item from the queue
        queue_index = self._get_item_queue_index(queue_id=queue_id)
        if queue_index is not None:
            self.queue.pop(queue_index)

        return True

    def _get_item_queue_index(self, queue_id):
        """
        This returns the index of a queue item in the queue list based on its queue_id
        """

        # self.queue is a list of queue_ids
        # so we can just return the index of the queue_id in the list
        try:
            return self.queue.index(queue_id)

        # if the queue_id is not found, return None
        except ValueError:
            return None

    def _item_can_start(self, queue_id, item_data=None):
        """
        This determines if a certain item can start based on its dependencies
        If any of its dependencies has failed, this will return None
        """

        if item_data is None:
            item_data = self.get_item(queue_id=queue_id)

        # if the item was canceled, done or failed, it cannot start
        if 'status' in item_data and item_data['status'] in ['canceled', 'done', 'failed']:

            # remove it from the queue
            queue_index = self._get_item_queue_index(queue_id=queue_id)
            if queue_index is not None:
                self.queue.pop(queue_index)

            return None

        # if the item has no dependencies, it can start
        if 'dependencies' not in item_data:
            return True

        # if the item has dependencies, check if they are all completed
        for dependency_id in item_data['dependencies']:

            dependency_item_data = self.get_item(queue_id=dependency_id)

            # if the dependency has failed or doesn't exist, return None
            # and mark the current item as failed as well
            if not dependency_item_data \
                    or ('status' in dependency_item_data
                        and dependency_item_data['status'] == 'failed'):

                logger.warning('Dependency {} failed or not available. '
                               'Item {} will fail too.'.format(dependency_id, queue_id))

                # the current item will also fail
                self.update_queue_item(queue_id=queue_id, status='failed')

                # remove it from the queue
                queue_index = self._get_item_queue_index(queue_id=queue_id)
                if queue_index is not None:
                    self.queue.pop(queue_index)

                return None

            # if the status of the dependency is not in the item data,
            # it could be that the dependency is still running or has not been started yet
            elif 'status' not in dependency_item_data or dependency_item_data['status'] != 'done':
                logger.debug('Dependency {} not completed yet. Try again later.'.format(dependency_id))
                return False

        return True

    def add_thread_to_queue_threads(self, device, queue_id, thread):
        """
        This function adds a thread to the queue_threads dict
        (it will replace anything related to that device without checking if the old thread is still running!)
        """

        # if the device is not in the queue_threads dict, add it
        self.queue_threads[device] = {'queue_id': queue_id, 'thread': thread}

        return self.queue_threads

    def remove_thread_from_queue_threads(self, device):
        """
        This function removes a thread from the queue_threads dict
        """

        if device is None:
            logger.warning('Unable to remove thread from queue threads - no device specified')

        # if the device is in the queue_threads dict, remove it
        if device in self.queue_threads:
            self.queue_threads.pop(device)

        return self.queue_threads

    def is_device_available(self, device):
        """
        This function checks if a device is busy processing something by checking the queue_threads dict.
        There's no way, of course, to know if the device is busy with some other process,
        but this helps keep the queue running smoothly internally.
        """

        # if the device is in the queue_threads dict, it's busy
        if device in self.queue_threads:

            # check if the thread is still running
            if self.queue_threads[device]['thread'].is_alive():

                # if it's still running, it's busy
                return False

            # if it's not running, it's not busy so remove it from the queue_threads dict
            else:
                self.remove_thread_from_queue_threads(device)

        return True

    def is_item_in_thread(self, queue_id):
        """
        This function checks if a queue item is in the queue_threads dict
        """

        for device in self.queue_threads:
            if queue_id == self.queue_threads[device]['queue_id']:
                return True

        return False

    def save_queue_to_file(self):
        """
        This function saves the queue history to the queue file
        """

        # get all the queue items
        queue_items = self.queue_history

        # if we don't have a list of queue items, create an empty one
        if not isinstance(queue_items, list):
            queue_items = []

        # we need to clean up the task_queue list before saving it to file
        # because we're unable to serialize the task_queue items with the thread objects
        # but, no worries, when we load the queue from file,
        # the add_to_queue function will dispatch the tasks again as needed
        # also, we don't need the output saved to the file
        save_queue_items = []
        for item in queue_items:
            save_item = {k: v for k, v in item.items() if k not in ('task_queue', 'last_task', 'output')}
            save_queue_items.append(save_item)

        # save the queue items to the queue json file
        try:
            with open(QUEUE_FILE_PATH, 'w') as f:
                json.dump(save_queue_items, f, indent=4)
                return True

        except Exception as e:
            logger.error('Could not save queue to file: {}'.format(e))
            return False

    def load_queue_from_file(self):
        """
        Reads the queue from the queue file
        """

        # the empty queue history list
        queue_history = []

        try:
            if os.path.exists(QUEUE_FILE_PATH):
                with open(QUEUE_FILE_PATH, 'r') as f:
                    queue_history = json.load(f)

        except Exception as e:
            logger.error('Could not load queue from file: {}'.format(e))

        return queue_history

    def resume_queue_from_file(
        self,
        ignore_finished=True,
    ):
        """
        Load saved queue items and restore unfinished processing jobs.

        Args:
            ignore_finished: Whether completed, failed and canceled items
                should be omitted from the restored queue history.

        Returns:
            True when unfinished queue items were restored, otherwise False.
        """

        queue_history = self.load_queue_from_file()

        # use this to determine what we return
        queue_empty = True

        # if we have a list
        if isinstance(queue_history, list) and len(queue_history) > 0:

            # rebuild the complete history only when finished items
            # should remain visible after restarting the application
            if not ignore_finished:
                self.queue_history = queue_history

            # take each item in the queue history and add it to the queue
            for idx, item in enumerate(queue_history):

                # skip if there's no queue_id or either the source_file_path or task_data is missing
                # it doesn't make sense to put it back in the queue since we can't do anything with it
                if not item.get('queue_id', None) \
                        or not (item.get('source_file_path', None) or item.get('task_data', None)):

                    # remove unusable items from the restored history
                    # so they are not written back into the queue file
                    if not ignore_finished:
                        self.queue_history.pop(idx)

                    continue

                # reset any progress
                if 'progress' in item:
                    del item['progress']

                # if it has no status, just queue it
                if 'status' not in item:
                    item['status'] = 'queued'

                    # add to the queue
                    # (but don't ping the queue yet)
                    self.add_to_queue(**item, ping=False)

                    continue

                # if the status is 'canceling', cancel it
                if item['status'] == 'canceling':
                    item['status'] = 'canceled'
                    continue

                # if the status is not ['done', 'failed', 'canceled'] add it to the queue
                # (but don't ping the queue yet)
                if item['status'] not in ['done', 'failed', 'canceled']:
                    self.add_to_queue(**item, ping=False)

                    queue_empty = False

            # once we finished re-building the queue, we need to ping it
            # it's important to ping it after we're done adding all items to the queue
            # since some items that depend on others might fail if they can't find the other items
            self.ping_queue()

            # if we processed the queue, return whether or not it's empty
            return not queue_empty

        # if we reached this point, we don't have a queue to resume
        return False
