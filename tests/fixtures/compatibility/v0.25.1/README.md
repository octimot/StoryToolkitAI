# Version 0.25.1 compatibility fixtures

These fixtures are small, synthetic, and sanitized. They contain no copied
user content or media.

Their field shapes were prepared from the serializers in the `v0.25.1` tag
(`14f38655e6fbf73a2912353b5830d90a9109ff53`) and then reduced to the values
needed for Version 1 compatibility tests:

- `project.json` uses the six project fields written by `Project.to_dict()`;
- `interview.transcription.json` uses the transcription and segment fields
  accepted and written by `Transcription` and `TranscriptionSegment`;
- `assembly.story.json` uses the story and story-line fields accepted and
  written by `Story` and `StoryLine`;
- `queue.json` uses the persistent queue-item fields written by
  `ProcessingQueue.save_queue_to_file()`;
- the `.srt` and `.txt` files pin representative deterministic exports from
  the transcription and story fixtures.

Names, IDs, paths, text, and timestamps were invented for the tests.
`compatibility_extension` and the nested extension values are deliberate
sentinels proving that transcription and story data not recognized by the
current model survives a load/save cycle.

The fixtures do not claim to represent every historical file variation.
Before the Version 1 release, copies of real user data from the current
stable release must still be checked with the applicable manual platform
release checklist.
