import time
import threading
import utils # Import module to access updated global variable

def mock_send_email(i):
    print(f"[{time.time():.2f}] Task {i}: STARTED (Thread: {threading.current_thread().name})")
    time.sleep(2)
    print(f"[{time.time():.2f}] Task {i}: FINISHED")

if __name__ == "__main__":
    current_limit = utils.get_current_thread_limit()
    print(f"Original Configured Limit: {current_limit}")
    
    print("Setting limit to 2 workers...")
    utils.update_email_thread_limit(2)
    print(f"New Configured Limit: {utils.get_current_thread_limit()}")
    
    print(f"Executor Max Workers: {utils.email_executor._max_workers}")
    
    for i in range(1, 6):
        f = utils.email_executor.submit(mock_send_email, i)
        futures.append(f)
        print(f"[{time.time():.2f}] Task {i}: SUBMITTED")

    print("\nWaiting for completion...")
    for f in futures:
        f.result()
    
    end_time = time.time()
    print(f"\nAll tasks completed in {end_time - start_time:.2f} seconds.")
    
    utils.update_email_thread_limit(5)
