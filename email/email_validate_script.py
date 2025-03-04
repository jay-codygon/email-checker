import re
import socket
import smtplib
import dns.resolver
from dns.exception import DNSException

def is_email_format_valid(email):
    """Check if email format is valid using regex."""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, email))

def verify_email_smtp(email, timeout=15):
    """Verify if email exists by performing an SMTP check with better error handling."""
    # Parse email parts
    try:
        username, domain = email.split('@')
    except ValueError:
        return False, "Invalid email format (missing @ symbol)"
    
    sender_email = "emeraldgreen@example.com"  # Your verification email
    
    # Get mail server MX records
    try:
        records = dns.resolver.resolve(domain, 'MX')
        mx_records = [str(r.exchange) for r in records]
        if not mx_records:
            return False, f"No MX records found for domain {domain}"
    except DNSException as e:
        return False, f"DNS error: {str(e)}"
    except Exception as e:
        return False, f"Error resolving MX records: {str(e)}"
    
    # Try each MX record until one works
    for mx_record in mx_records:
        smtp = smtplib.SMTP(timeout=timeout)
        smtp.set_debuglevel(0)  # Set to 1 for debugging
        
        try:
            # Connect to the mail server
            smtp.connect(mx_record)
            smtp.helo(socket.getfqdn())
            smtp.mail(sender_email)
            
            # This is where the actual verification happens
            code, message = smtp.rcpt(email)
            smtp.quit()
            
            # SMTP server accepted the recipient
            if code == 250:
                return True, "Email exists"
            else:
                # Continue trying other MX servers
                continue
                
        except smtplib.SMTPServerDisconnected:
            continue
        except smtplib.SMTPConnectError:
            continue
        except socket.timeout:
            continue
        except Exception as e:
            continue
    
    # If we get here, none of the MX servers validated the email
    return False, "Email validation failed or timed out. This doesn't necessarily mean the email is invalid - many servers block SMTP verification."

def check_email(email):
    """Complete email validation function."""
    # First check format
    if not is_email_format_valid(email):
        return False, "Invalid email format"
    
    # Then perform SMTP check
    return verify_email_smtp(email)

# Example usage
if __name__ == "__main__":
    email_to_check = input("Enter email to verify: ")
    is_valid, message = check_email(email_to_check)
    
    print(f"Format check: {'✅ Valid' if is_email_format_valid(email_to_check) else '❌ Invalid'}")
    print(f"SMTP check: {'✅ ' if is_valid else '❓ '}{message}")
    
    if not is_valid and is_email_format_valid(email_to_check):
        print("\nNOTE: Many email providers block SMTP verification for security reasons.")
        print("A failed SMTP check does NOT guarantee the email is invalid.")
        print("For critical applications, consider email verification via sending a confirmation link.")