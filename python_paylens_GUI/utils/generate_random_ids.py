import uuid as UUID
def generate_uuid():
    return str(UUID.uuid4())

def generate_event_id():
    return "evt_" + generate_uuid()     

def generate_payment_id():
    return "pay_" + generate_uuid()

def generate_attempt_id():
    return "attempt_" + generate_uuid() 

def generate_order_reference():
    return "ord_" + generate_uuid()

def generate_idempotency_key():
    return "idem_" + generate_uuid()

def generate_processor_reference():
    return "proc_" + generate_uuid()

def generate_aurhorization_code():
    return "AUTH" + str(UUID.uuid4().int)[:6]

def generate_capture_id():  
    return "cap_" + generate_uuid()