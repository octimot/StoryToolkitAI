"""
TwelveLabs backend for StoryToolkitAI.

This is an optional, opt-in backend that lets the tool use TwelveLabs' video
foundation models instead of (or alongside) the built-in local CLIP indexing:

- Marengo for semantic footage search over a TwelveLabs index
- Pegasus for content understanding (describe / summarise / answer questions
  about a clip)

It is completely off by default. Nothing here runs unless the user adds a
TwelveLabs API key to the app config (the "twelvelabs_api_key" setting) and
explicitly calls into this backend, so the local indexing and search behaviour
is left untouched.

The TwelveLabs Python SDK (`twelvelabs`) is imported lazily so that users who
don't enable this backend don't need the package installed at all.

You can grab a free API key at https://twelvelabs.io - there's a generous free
tier.
"""

import os

from storytoolkitai.core.logger import logger

# the embedding model used for text -> vector queries (Marengo)
DEFAULT_MARENGO_MODEL = 'marengo3.0'

# the analysis model used for content understanding (Pegasus)
DEFAULT_PEGASUS_MODEL = 'pegasus1.2'


class TwelveLabsBackend:
    """
    Thin wrapper around the TwelveLabs SDK that exposes the two features that
    map onto StoryToolkitAI: semantic footage search (Marengo) and content
    understanding (Pegasus).

    The API key is read, in order of priority, from:
        1. the api_key passed to the constructor
        2. the app config setting "twelvelabs_api_key" (via the stAI object)
        3. the TWELVELABS_API_KEY environment variable

    If no key is found, instantiation raises ValueError - this keeps the
    backend strictly opt-in and avoids silently degrading the local search.
    """

    __version__ = '0.1'

    def __init__(self, api_key: str = None, stAI=None,
                 marengo_model: str = DEFAULT_MARENGO_MODEL,
                 pegasus_model: str = DEFAULT_PEGASUS_MODEL):

        self.stAI = stAI
        self.marengo_model = marengo_model
        self.pegasus_model = pegasus_model

        # resolve the api key from the constructor, the config or the environment
        self.api_key = api_key

        if not self.api_key and stAI is not None:
            self.api_key = stAI.get_app_setting(setting_name='twelvelabs_api_key', default_if_none=None)

        if not self.api_key:
            self.api_key = os.environ.get('TWELVELABS_API_KEY', None)

        if not self.api_key:
            raise ValueError(
                'No TwelveLabs API key found. Add a "twelvelabs_api_key" to the app settings '
                'or set the TWELVELABS_API_KEY environment variable to use the TwelveLabs backend.'
            )

        # the SDK client is created lazily on first use
        self._client = None

    @property
    def client(self):
        """
        Lazily create (and cache) the TwelveLabs SDK client.
        The SDK is imported here so the dependency is only required when the
        backend is actually used.
        """

        if self._client is None:
            try:
                from twelvelabs import TwelveLabs
            except ImportError:
                logger.error(
                    'The "twelvelabs" package is not installed. '
                    'Install it with "pip install twelvelabs" to use the TwelveLabs backend.'
                )
                raise

            self._client = TwelveLabs(api_key=self.api_key)

        return self._client

    def embed_text(self, query: str):
        """
        Encode a text query into a Marengo embedding vector (a list of floats).

        This mirrors the role of CLIP's encode_text in the local backend, so it
        can be used to compare a query against pre-computed footage embeddings.

        :param query: the text to embed
        :return: a list of floats (the embedding), or None on failure
        """

        if not query:
            return None

        try:
            response = self.client.embed.create(model_name=self.marengo_model, text=query)
        except Exception as e:
            logger.error('TwelveLabs embedding failed: {}'.format(e))
            return None

        # the text embedding lives in response.text_embedding.segments[0].float_
        text_embedding = getattr(response, 'text_embedding', None)
        if text_embedding is None or not getattr(text_embedding, 'segments', None):
            logger.warning('TwelveLabs returned no text embedding for query: {}'.format(query))
            return None

        return text_embedding.segments[0].float_

    def search(self, query: str, index_id: str, max_results: int = 5,
               search_options: list = None):
        """
        Semantic footage search over a TwelveLabs index using Marengo.

        The result list mirrors the shape used by the local VideoSearch backend
        (one dict per match, with a "score" and the time range), so it can be
        consumed by the same UI code:

            [
                {
                    'video_id': <str>,
                    'score': <float>,        # 0-100, higher is better
                    'start': <float>,        # clip start in seconds
                    'end': <float>,          # clip end in seconds
                    'thumbnail_url': <str or None>,
                },
                ...
            ]

        :param query: the natural language search query
        :param index_id: the TwelveLabs index to search in
        :param max_results: maximum number of clips to return
        :param search_options: which modalities to search (defaults to ['visual', 'audio'])
        :return: a list of result dicts (possibly empty), or None on failure
        """

        if not query or not index_id:
            logger.warning('TwelveLabs search needs both a query and an index_id.')
            return None

        if search_options is None:
            search_options = ['visual', 'audio']

        try:
            response = self.client.search.create(
                index_id=index_id,
                search_options=search_options,
                query_text=query,
                page_limit=max_results,
            )
        except Exception as e:
            logger.error('TwelveLabs search failed: {}'.format(e))
            return None

        results = []
        for item in (getattr(response, 'data', None) or [])[:max_results]:
            results.append({
                'video_id': getattr(item, 'video_id', None),
                # the SDK exposes a relevance score on most plans; fall back to
                # the inverse rank when it isn't present so callers can sort
                'score': float(getattr(item, 'score', None)
                               if getattr(item, 'score', None) is not None
                               else -1 * (getattr(item, 'rank', 0) or 0)),
                'start': getattr(item, 'start', None),
                'end': getattr(item, 'end', None),
                'thumbnail_url': getattr(item, 'thumbnail_url', None),
            })

        return results

    def analyze(self, video_id: str, prompt: str, max_tokens: int = 2048,
                temperature: float = None):
        """
        Content understanding for an indexed video using Pegasus.

        Use this to describe, summarise or answer questions about a clip that
        has already been indexed in TwelveLabs.

        :param video_id: the id of an indexed TwelveLabs video
        :param prompt: the instruction / question (e.g. "Describe this video")
        :param max_tokens: max tokens in the generated text
        :param temperature: optional sampling temperature
        :return: the generated text (str), or None on failure
        """

        if not video_id or not prompt:
            logger.warning('TwelveLabs analyze needs both a video_id and a prompt.')
            return None

        kwargs = dict(
            model_name=self.pegasus_model,
            video_id=video_id,
            prompt=prompt,
            max_tokens=max_tokens,
        )

        if temperature is not None:
            kwargs['temperature'] = temperature

        try:
            response = self.client.analyze(**kwargs)
        except Exception as e:
            logger.error('TwelveLabs analyze failed: {}'.format(e))
            return None

        return getattr(response, 'data', None)

    def list_indexes(self):
        """
        Return the available TwelveLabs indexes as a list of (id, name) tuples.
        Useful for letting the user pick an index in the UI.
        """

        try:
            return [
                (getattr(idx, 'id', None), getattr(idx, 'index_name', None))
                for idx in self.client.indexes.list()
            ]
        except Exception as e:
            logger.error('Could not list TwelveLabs indexes: {}'.format(e))
            return None
