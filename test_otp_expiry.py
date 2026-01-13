import time
from flask import Flask, session
from utils import store_otp_in_session, verify_otp_in_session

app = Flask(__name__)
app.secret_key = 'test_secret'

def test_otp_flow():
    with app.test_request_context():
        print("1. Testing Standard Flow (Immediate)")
        store_otp_in_session('test_otp', '123456')
        is_valid, msg = verify_otp_in_session('test_otp', '123456')
        print(f"   Result: {is_valid}, Msg: {msg}")
        assert is_valid == True, "Standard flow failed"
        
        print("\n2. Testing Wrong OTP")
        store_otp_in_session('test_otp_2', '654321')
        is_valid, msg = verify_otp_in_session('test_otp_2', 'wrong')
        print(f"   Result: {is_valid}, Msg: {msg}")
        assert is_valid == False, "Wrong OTP should fail"
        
        print("\n3. Testing Expiration (Mocked Time)")
        # Store OTP
        print("\n3. Testing Expiration (Mocked Time)")
        
        store_otp_in_session('test_otp_expiry', '111222')
        
        session['test_otp_expiry_time'] = int(time.time()) - 601
        
        is_valid, msg = verify_otp_in_session('test_otp_expiry', '111222')
        print(f"   Result: {is_valid}, Msg: {msg}")
        assert is_valid == False and "expired" in msg.lower(), "Expiration failed"
        
        print("\nSUCCESS: All OTP logic tests passed.")

if __name__ == "__main__":
    test_otp_flow()
