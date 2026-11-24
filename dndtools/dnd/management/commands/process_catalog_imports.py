import signal
from threading import Event

from django.core.management.base import BaseCommand
from django.db import DatabaseError, close_old_connections, connections

from dnd.editorial_batches import process_next_batch


class Command(BaseCommand):
    help = 'Process queued catalog imports and their publication notifications.'

    def handle(self, *args, **options):
        stop = Event()

        def request_stop(*args):
            stop.set()

        signal.signal(signal.SIGTERM, request_stop)
        signal.signal(signal.SIGINT, request_stop)
        self.stdout.write('Catalog import worker ready.')
        while not stop.is_set():
            try:
                close_old_connections()
                if process_next_batch():
                    continue
            except DatabaseError as error:
                self.stderr.write(f'Catalog import worker database error ({type(error).__name__}). Retrying.')
                connections.close_all()
            stop.wait(3)
