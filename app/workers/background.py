import threading

def run_async(task, *args, **kwargs):
    thread = threading.Thread(target=task, args=args, kwargs=kwargs)
    thread.start()