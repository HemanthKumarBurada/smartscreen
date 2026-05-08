import aiosmtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from app.config import settings

async def send_email(to: str, subject: str, html_body: str):
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = f"{settings.MAIL_FROM_NAME} <{settings.MAIL_FROM}>"
    msg["To"] = to
    msg.attach(MIMEText(html_body, "html"))

    await aiosmtplib.send(
        msg,
        hostname="smtp.gmail.com",
        port=587,
        start_tls=True,
        username=settings.MAIL_USERNAME,
        password=settings.MAIL_PASSWORD,
    )

async def send_recording_link(candidate_name: str, candidate_email: str, token: str, job_title: str):
    link = f"{settings.APP_URL}/record/{token}"
    html = f"""
    <div style="font-family:Arial,sans-serif;max-width:600px;margin:0 auto;">
      <h2 style="color:#4F46E5;">SmartScreen — Next Step</h2>
      <p>Dear <b>{candidate_name}</b>,</p>
      <p>Your resume for <b>{job_title}</b> has been reviewed. 
         You have been shortlisted for the video screening round.</p>
      <p>Please record a <b>2–3 minute self-introduction</b> using the link below. 
         Speak about your background, skills, and why you're a good fit.</p>
      <div style="text-align:center;margin:30px 0;">
        <a href="{link}" style="background:#4F46E5;color:white;padding:14px 28px;
           border-radius:8px;text-decoration:none;font-size:16px;">
          🎥 Start Live Recording
        </a>
      </div>
      <p style="color:#666;">⏰ This link is valid for 48 hours.</p>
      <p style="color:#666;font-size:12px;">Make sure your camera and microphone are enabled.</p>
    </div>
    """
    await send_email(candidate_email, f"Action Required: Video Screening for {job_title}", html)

async def send_result_email(
    candidate_name: str,
    candidate_email: str,
    job_title: str,
    final_score: float,
    is_qualified: bool,
    recommendations: list[str] | None = None
):
    if is_qualified:
        subject = f"✅ Congratulations! You've been shortlisted for {job_title}"
        status_html = f"""
        <div style="background:#D1FAE5;padding:20px;border-radius:8px;text-align:center;">
          <h2 style="color:#065F46;">🎉 You are Qualified!</h2>
          <p style="font-size:24px;font-weight:bold;color:#047857;">
            Score: {final_score:.1f}%
          </p>
          <p>Our HR team will contact you shortly with the next steps.</p>
        </div>
        """
    else:
        subject = f"Application Update — {job_title}"
        status_html = f"""
        <div style="background:#FEE2E2;padding:20px;border-radius:8px;text-align:center;">
          <h2 style="color:#991B1B;">Application Not Selected</h2>
          <p style="font-size:24px;font-weight:bold;color:#DC2626;">
            Score: {final_score:.1f}%
          </p>
          <p>Thank you for your time. We encourage you to apply again.</p>
        </div>
        """

    # ── Recommendations Section ─────────────────────────────
    recommendations_html = ""

    if recommendations:
        recommendations_html = """
        <div style="margin-top:30px;">
          <h3 style="color:#4F46E5;">Personalized Recommendations</h3>
          <ul style="padding-left:20px;">
        """

        for rec in recommendations:
            recommendations_html += f"""
            <li style="margin-bottom:10px;line-height:1.5;">
              {rec}
            </li>
            """

        recommendations_html += """
          </ul>
        </div>
        """

    html = f"""
    <div style="font-family:Arial,sans-serif;max-width:650px;margin:0 auto;padding:20px;">

      <h2 style="color:#4F46E5;">
        SmartScreen — Application Result
      </h2>

      <p>Dear <b>{candidate_name}</b>,</p>

      <p>
        Here is the result of your application for
        <b>{job_title}</b>:
      </p>

      {status_html}

      {recommendations_html}

      <hr style="margin:30px 0;">

      <p style="font-size:13px;color:#666;">
        This evaluation was generated automatically using SmartScreen AI.
      </p>

    </div>
    """

    await send_email(candidate_email, subject, html)