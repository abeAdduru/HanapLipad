import os
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail

def send_price_alert_email(recipient_email, flight, average_price):
    """
    Sends a price alert email using SendGrid.
    """
    sender_email = os.getenv("SENDER_EMAIL")
    api_key = os.getenv("SENDGRID_API_KEY")

    if not all([sender_email, api_key]):
        print("Sender email or SendGrid API key is not set. Cannot send email.")
        return

    message = Mail(
        from_email=sender_email,
        to_emails=recipient_email,
        subject=f"✈️ Price Drop Alert! Cheap Flights to {flight.destination}!",
        html_content=f"""
        <div style="font-family: Arial, sans-serif; line-height: 1.6;">
            <h2>🎉 Good News! We Found a Cheap Flight! 🎉</h2>
            <p>
                A flight from <strong>{flight.origin}</strong> to <strong>{flight.destination}</strong> on 
                <strong>{flight.date.strftime('%B %d, %Y')}</strong> has dropped to an amazing price!
            </p>
            <h3 style="color: #28a745;">Price: ¥{flight.price:,.0f}</h3>
            <p>
                This is below the current 30-day average price of ¥{average_price:,.0f}.
            </p>
            <p>
                This is a great time to book! Prices can change quickly.
            </p>
            <a href="https://www.google.com/flights" 
               style="background-color: #007bff; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px;">
               Search for Flights Now
            </a>
            <br><br>
            <p>Happy travels!</p>
        </div>
        """
    )
    try:
        sg = SendGridAPIClient(api_key)
        response = sg.send(message)
        print(f"Price alert email sent to {recipient_email}. Status code: {response.status_code}")
    except Exception as e:
        print(f"Error sending email: {e}")