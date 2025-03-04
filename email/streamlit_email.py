import streamlit as st
import pandas as pd
import re
import socket
import smtplib
import dns.resolver
from dns.exception import DNSException
import io
import time

# Set page title and description
st.set_page_config(page_title="Email Validator", page_icon="✉️")
st.title("Email Validator Tool")
st.write("Upload a CSV or Excel file with an email column to validate email addresses for format and reachability.")

def is_email_format_valid(email):
    """Check if email format is valid using regex."""
    if pd.isna(email):
        return False
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, str(email)))

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

# File uploader
uploaded_file = st.file_uploader("Choose a CSV or Excel file", type=["csv", "xlsx", "xls"])

if uploaded_file is not None:
    # Read the file
    try:
        if uploaded_file.name.endswith('.csv'):
            df = pd.read_csv(uploaded_file)
        else:
            df = pd.read_excel(uploaded_file)
        
        # Check if file has data
        if df.empty:
            st.error("The uploaded file is empty!")
        else:
            st.success("File successfully loaded!")
            st.write("Preview of uploaded data:")
            st.dataframe(df.head())
            
            # Email column selection
            all_columns = df.columns.tolist()
            email_col = st.selectbox("Select the email column", all_columns)
            
            if st.button("Validate Emails"):
                if email_col:
                    # Add progress bar
                    progress_bar = st.progress(0)
                    status_text = st.empty()
                    
                    # Add result columns
                    df['format_valid'] = False
                    df['reachable'] = False
                    df['validation_message'] = ""
                    
                    # Process each email
                    total_rows = len(df)
                    
                    for i, row in df.iterrows():
                        email = str(row[email_col])
                        progress_percent = (i + 1) / total_rows
                        
                        status_text.text(f"Processing {i+1} of {total_rows}: {email}")
                        
                        # Check format first
                        format_valid = is_email_format_valid(email)
                        df.at[i, 'format_valid'] = format_valid
                        
                        if format_valid:
                            # Only check reachability if format is valid
                            is_reachable, message = verify_email_smtp(email)
                            username, domain = email.split('@')
                            df.at[i, 'username'] = username
                            df.at[i, 'domain'] = domain
                            df.at[i, 'reachable'] = is_reachable
                            df.at[i, 'validation_message'] = message
                        else:
                            df.at[i, 'validation_message'] = "Invalid email format"
                        
                        # Update progress
                        progress_bar.progress(progress_percent)
                        
                        # Add small delay to avoid rate limiting
                        time.sleep(0.1)
                    
                    status_text.text("Email validation complete!")
                    
                    # Show results
                    st.subheader("Validation Results")
                    st.dataframe(df)
                    
                    # Prepare download link
                    csv = df.to_csv(index=False).encode('utf-8')
                    
                    st.download_button(
                        label="Download Results as CSV",
                        data=csv,
                        file_name="email_validation_results.csv",
                        mime="text/csv",
                    )
                    
                    # Summary
                    valid_format_count = df['format_valid'].sum()
                    reachable_count = df['reachable'].sum()
                    
                    st.subheader("Summary")
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.metric("Total Emails", total_rows)
                    with col2:
                        st.metric("Valid Format", f"{valid_format_count} ({valid_format_count/total_rows*100:.1f}%)")
                    with col3:
                        st.metric("Reachable", f"{reachable_count} ({reachable_count/total_rows*100:.1f}%)")
                    
                    st.info("""
                    📌 Note: Many email providers block SMTP verification for security reasons.
                    A failed SMTP check does NOT guarantee the email is invalid.
                    For critical applications, consider email verification via sending a confirmation link.
                    """)
                else:
                    st.error("Please select the email column!")
    
    except Exception as e:
        st.error(f"Error processing file: {e}")

# Add some information about the app
st.sidebar.header("About")
st.sidebar.info("""
This app validates emails in two ways:
1. **Format Check**: Verifies that the email follows the correct pattern (user@domain.tld)
2. **SMTP Check**: Attempts to verify if the email address exists on the mail server

Upload your file, select the email column, and click 'Validate Emails' to begin.
""")

# Add warning about SMTP validation limitations
st.sidebar.warning("""
⚠️ SMTP validation has limitations:
- Many mail servers block verification attempts
- Rate limiting may affect results for large lists
- Results are not 100% reliable
""")

# Requirements information
st.sidebar.header("Requirements")
st.sidebar.code("""
pip install streamlit pandas dnspython
""")