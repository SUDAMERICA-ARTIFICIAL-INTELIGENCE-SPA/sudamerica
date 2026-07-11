"""HTML email templates for Sudamérica AI transactional emails."""

_BASE_STYLE = """
<style>
  body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; margin: 0; padding: 0; background: #f4f5f7; }
  .container { max-width: 520px; margin: 40px auto; background: #ffffff; border-radius: 12px; overflow: hidden; box-shadow: 0 2px 8px rgba(0,0,0,0.06); }
  .header { background: linear-gradient(135deg, #FF4757 0%, #FFB800 40%, #0099FF 70%, #00B894 100%); padding: 28px 32px; text-align: center; }
  .header h1 { color: #fff; font-size: 22px; margin: 0; font-weight: 800; letter-spacing: -0.5px; }
  .body { padding: 32px; color: #212529; line-height: 1.6; font-size: 15px; }
  .body h2 { font-size: 18px; margin: 0 0 16px 0; color: #1a1b1e; }
  .btn { display: inline-block; background: linear-gradient(135deg, #4C6EF5, #0099FF); color: #fff !important; text-decoration: none; padding: 12px 32px; border-radius: 8px; font-weight: 600; font-size: 15px; margin: 20px 0; }
  .code-box { background: #f8f9fa; border: 2px dashed #dee2e6; border-radius: 8px; padding: 16px; text-align: center; font-size: 28px; font-weight: 700; letter-spacing: 4px; color: #4C6EF5; margin: 16px 0; }
  .footer { padding: 20px 32px; text-align: center; font-size: 12px; color: #868e96; border-top: 1px solid #f1f3f5; }
  .footer a { color: #4C6EF5; text-decoration: none; }
  .muted { color: #868e96; font-size: 13px; }
</style>
"""


def password_reset_email(reset_url: str, nombre: str, expiry_minutes: int = 60) -> tuple[str, str]:
    """Return (plain_text, html) for password reset email."""
    plain = (
        f"Hola {nombre},\n\n"
        f"Recibimos una solicitud para restablecer tu contraseña en Sudamérica AI.\n\n"
        f"Haz clic en el siguiente enlace para crear una nueva contraseña:\n{reset_url}\n\n"
        f"Este enlace expira en {expiry_minutes} minutos.\n\n"
        f"Si no solicitaste este cambio, ignora este correo.\n\n"
        f"— Equipo Sudamérica AI"
    )
    html = f"""<!DOCTYPE html><html><head>{_BASE_STYLE}</head><body>
<div class="container">
  <div class="header"><h1>Sudamérica AI</h1></div>
  <div class="body">
    <h2>Restablecer contraseña</h2>
    <p>Hola <strong>{nombre}</strong>,</p>
    <p>Recibimos una solicitud para restablecer tu contraseña.</p>
    <p style="text-align:center"><a href="{reset_url}" class="btn">Crear nueva contraseña</a></p>
    <p class="muted">Este enlace expira en {expiry_minutes} minutos. Si no solicitaste este cambio, ignora este correo.</p>
  </div>
  <div class="footer">Sudamérica AI &mdash; Gastronomia inteligente<br><a href="https://sudamerica.ai">sudamerica.ai</a></div>
</div>
</body></html>"""
    return plain, html


def email_verification_email(verify_url: str, nombre: str, code: str) -> tuple[str, str]:
    """Return (plain_text, html) for email verification."""
    plain = (
        f"Hola {nombre},\n\n"
        f"Bienvenido a Sudamérica AI! Verifica tu email con el siguiente codigo:\n\n"
        f"{code}\n\n"
        f"O haz clic aqui: {verify_url}\n\n"
        f"— Equipo Sudamérica AI"
    )
    html = f"""<!DOCTYPE html><html><head>{_BASE_STYLE}</head><body>
<div class="container">
  <div class="header"><h1>Sudamérica AI</h1></div>
  <div class="body">
    <h2>Verifica tu email</h2>
    <p>Hola <strong>{nombre}</strong>, bienvenido a Sudamérica AI!</p>
    <p>Usa este codigo para verificar tu cuenta:</p>
    <div class="code-box">{code}</div>
    <p style="text-align:center">O haz clic directamente:</p>
    <p style="text-align:center"><a href="{verify_url}" class="btn">Verificar email</a></p>
  </div>
  <div class="footer">Sudamérica AI &mdash; Gastronomia inteligente<br><a href="https://sudamerica.ai">sudamerica.ai</a></div>
</div>
</body></html>"""
    return plain, html


def welcome_email(nombre: str, login_url: str) -> tuple[str, str]:
    """Return (plain_text, html) for welcome email after verification."""
    plain = (
        f"Hola {nombre},\n\n"
        f"Tu cuenta en Sudamérica AI ha sido verificada exitosamente!\n\n"
        f"Ya puedes acceder a tu dashboard: {login_url}\n\n"
        f"— Equipo Sudamérica AI"
    )
    html = f"""<!DOCTYPE html><html><head>{_BASE_STYLE}</head><body>
<div class="container">
  <div class="header"><h1>Sudamérica AI</h1></div>
  <div class="body">
    <h2>Cuenta verificada!</h2>
    <p>Hola <strong>{nombre}</strong>,</p>
    <p>Tu cuenta esta lista. Ya puedes gestionar tu restaurante con inteligencia artificial.</p>
    <p style="text-align:center"><a href="{login_url}" class="btn">Ir a mi dashboard</a></p>
  </div>
  <div class="footer">Sudamérica AI &mdash; Gastronomia inteligente<br><a href="https://sudamerica.ai">sudamerica.ai</a></div>
</div>
</body></html>"""
    return plain, html
