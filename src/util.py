
def convert_str_to_milliunits(str_val):
    # check that it can be converted to int
    # If there's no decimal assume it's a dollar value
    if '.' not in str_val:
        return int(str_val) * 1000
    
    # Check that there's a single decimal, and only 2 decimal places
    return int(str_val.replace('.','')) * 10

def convert_milliunits_to_str(val):
    return '${:.2f}'.format(val/1000)
