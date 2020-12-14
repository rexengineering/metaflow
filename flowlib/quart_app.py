import asyncio
import logging
import signal
from typing import Any

from quart import Quart
from hypercorn.config import Config
from hypercorn.asyncio import serve


class QuartApp:
    def __init__(self, name, **kws):
        self.app = Quart(name)
        self.config = Config.from_mapping(kws)
        self.shutdown_event = asyncio.Event()

    def _shutdown(self):
        pass

    def _termination_handler(self, *_: Any, exn: Exception = None) -> None:
        if exn:
            logging.exception(exn)
            logging.info(f'Shutting down {self.app.name} daemon...')
        else:
            logging.info(
                f'SIGTERM received, shutting down {self.app.name} daemon...'
            )
        self._shutdown()
        self.shutdown_event.set()

    def run(self):
        logging.debug('QuartApp.run() called...')
        try:
            loop = asyncio.get_event_loop()
            loop.add_signal_handler(signal.SIGTERM, self._termination_handler)
            return loop.run_until_complete(serve(
                self.app, self.config, shutdown_trigger=self.shutdown_event.wait
            ))
        except (KeyboardInterrupt, Exception) as exn:
            self._termination_handler(exn=exn)
