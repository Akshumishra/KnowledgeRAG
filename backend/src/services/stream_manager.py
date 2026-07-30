import asyncio
import logging

logger = logging.getLogger(__name__)


class StreamManager:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance.buffers = {}
            cls._instance.clients = {}
            cls._instance.done = set()
        return cls._instance

    def initialize_stream(self, message_id: str):
        if message_id not in self.buffers:
            self.buffers[message_id] = []
        if message_id not in self.clients:
            self.clients[message_id] = set()

    async def push_event(self, message_id: str, event_string: str):
        if message_id not in self.buffers:
            self.buffers[message_id] = []

        self.buffers[message_id].append(event_string)

        if message_id in self.clients:
            for queue in list(self.clients[message_id]):
                try:
                    await queue.put(event_string)
                except (RuntimeError, asyncio.QueueFull) as e:
                    logger.error(f"Error putting event to queue: {e}")

    async def finish_stream(self, message_id: str):
        self.done.add(message_id)
        if message_id in self.clients:
            for queue in list(self.clients[message_id]):
                try:
                    await queue.put(None)
                except (RuntimeError, asyncio.QueueFull):
                    logger.debug("Could not put sentinel None to queue; already closed.")

        # We don't instantly delete the buffer because a client might connect right as it finishes.
        # But we remove the clients set to free memory.
        self.clients.pop(message_id, None)

        # Schedule cleanup of the buffer after 30 seconds
        asyncio.create_task(self._cleanup_later(message_id, 30))

    async def _cleanup_later(self, message_id: str, delay: int):
        await asyncio.sleep(delay)
        self.buffers.pop(message_id, None)
        self.done.discard(message_id)

    def is_done(self, message_id: str) -> bool:
        return message_id in self.done


stream_manager = StreamManager()
