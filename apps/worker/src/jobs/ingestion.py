from time import sleep

from src.utils.logging import log


def run_worker_loop() -> None:
    log("worker", "Worker RC7 iniciado. Esperando trabajos de ingesta...")
    while True:
        sleep(5)
        log("worker", "Heartbeat: worker activo.")
