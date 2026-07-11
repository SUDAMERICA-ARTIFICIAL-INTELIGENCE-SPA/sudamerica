"""Generate Sudamérica AI User Guide PDF with screenshots."""

import os
from fpdf import FPDF

BASE = "D:/Sudamérica.AI/MVP/MVP"
OUTPUT = os.path.join(BASE, "Sudamerica_Guia_Usuario.pdf")


class GuidePDF(FPDF):
    def header(self):
        if self.page_no() > 1:
            self.set_font("Helvetica", "I", 9)
            self.set_text_color(120, 120, 120)
            self.cell(0, 8, "Sudamérica AI - Guia del Usuario", align="L")
            self.cell(0, 8, f"Pagina {self.page_no()}", align="R")
            self.ln(12)

    def chapter_title(self, title):
        self.set_font("Helvetica", "B", 22)
        self.set_text_color(40, 40, 40)
        self.cell(0, 14, title, new_x="LMARGIN", new_y="NEXT")
        self.set_draw_color(76, 110, 245)
        self.set_line_width(0.8)
        self.line(10, self.get_y(), 200, self.get_y())
        self.ln(6)

    def section_text(self, text):
        self.set_font("Helvetica", "", 11)
        self.set_text_color(50, 50, 50)
        self.multi_cell(0, 6, text)
        self.ln(3)

    def bullet(self, text):
        self.set_font("Helvetica", "", 11)
        self.set_text_color(50, 50, 50)
        self.set_x(10)
        self.multi_cell(w=0, h=6, text=f"  -  {text}", new_x="LMARGIN", new_y="NEXT")

    def add_screenshot(self, img_path, caption=""):
        if not os.path.exists(img_path):
            return
        # Fit image to page width with margins
        img_w = 190
        self.image(img_path, x=10, w=img_w)
        if caption:
            self.set_font("Helvetica", "I", 9)
            self.set_text_color(100, 100, 100)
            self.cell(0, 5, caption, align="C", new_x="LMARGIN", new_y="NEXT")
        self.ln(4)


def build_pdf():
    pdf = GuidePDF("P", "mm", "A4")
    pdf.set_auto_page_break(auto=True, margin=15)

    # ── COVER ──
    pdf.add_page()
    pdf.ln(50)
    pdf.set_font("Helvetica", "B", 36)
    pdf.set_text_color(76, 110, 245)
    pdf.cell(0, 20, "Sudamérica AI", align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 16)
    pdf.set_text_color(80, 80, 80)
    pdf.cell(0, 10, "Gastronomia Inteligente", align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(10)
    pdf.set_font("Helvetica", "B", 20)
    pdf.set_text_color(40, 40, 40)
    pdf.cell(0, 12, "Guia Completa del Usuario", align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(20)
    pdf.set_font("Helvetica", "", 12)
    pdf.set_text_color(100, 100, 100)
    pdf.cell(0, 8, "Plataforma de inteligencia artificial para restaurantes", align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.cell(0, 8, "y negocios gastronomicos en Latinoamerica", align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(30)
    pdf.set_font("Helvetica", "I", 10)
    pdf.cell(0, 8, "Version 1.0 - Abril 2026", align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.cell(0, 8, "Sudamérica AI", align="C", new_x="LMARGIN", new_y="NEXT")

    # ── TABLE OF CONTENTS ──
    pdf.add_page()
    pdf.chapter_title("Contenido")
    toc = [
        "1. Registro e Inicio de Sesion",
        "2. Panel Principal (Reportes)",
        "3. Copiloto Admin (Sudamérica AI)",
        "4. Conversaciones IA (Prospectos)",
        "5. Rendimiento IA",
        "6. Configuracion IA",
        "7. Cocina - KDS (Comandas)",
        "8. Mesas del Restaurante",
        "9. Reservaciones",
        "10. Carta y Menu",
        "11. Clientes",
        "12. Equipo",
        "13. Configuracion del Restaurante",
    ]
    for item in toc:
        pdf.bullet(item)
    pdf.ln(10)
    pdf.section_text(
        "Esta guia cubre todas las secciones de Sudamérica AI. "
        "Cada capitulo incluye una captura de pantalla de la seccion "
        "y una explicacion detallada de su funcionamiento."
    )

    # ── 1. REGISTRO ──
    pdf.add_page()
    pdf.chapter_title("1. Registro e Inicio de Sesion")
    pdf.section_text(
        "Sudamérica AI ofrece un proceso de registro conversacional guiado por inteligencia artificial. "
        "Al hacer clic en 'Registrate gratis', un asistente virtual te guia paso a paso para "
        "configurar tu restaurante y tu agente de IA personalizado."
    )
    pdf.section_text("Durante el registro, la IA te pedira:")
    pdf.bullet("Nombre de tu restaurante y tipo de comida")
    pdf.bullet("Tus datos personales (nombre, email, contrasena)")
    pdf.bullet("Horario de atencion y zona de delivery")
    pdf.bullet("Una breve descripcion del negocio")
    pdf.bullet("El tono de comunicacion de tu agente IA (casual, formal o mixto)")
    pdf.ln(4)
    pdf.add_screenshot(f"{BASE}/guide_00_registro.png", "Pantalla de registro conversacional con Sudamérica AI")
    pdf.ln(4)
    pdf.section_text(
        "Una vez completado el registro, tu agente IA queda pre-configurado y listo para operar. "
        "Comenzaras con el plan Estandar (gratuito, hasta 100 clientes/mes)."
    )

    # Login
    pdf.add_page()
    pdf.section_text(
        "Para iniciar sesion, ingresa tu email y contrasena en la pantalla de login. "
        "Si olvidaste tu contrasena, puedes recuperarla desde el enlace '?Olvidaste tu contrasena?'."
    )
    pdf.add_screenshot(f"{BASE}/guide_01_login.png", "Pantalla de inicio de sesion")

    # ── 2. DASHBOARD / REPORTES ──
    pdf.add_page()
    pdf.chapter_title("2. Panel Principal (Reportes)")
    pdf.section_text(
        "Al iniciar sesion, llegas al panel de Reportes, el centro de control financiero "
        "de tu restaurante. Aqui puedes ver de un vistazo:"
    )
    pdf.bullet("Ingresos del dia: total de ventas en tiempo real")
    pdf.bullet("Pedidos entregados: cantidad de ordenes completadas")
    pdf.bullet("Items vendidos: total de productos vendidos")
    pdf.bullet("Ticket promedio: valor promedio por orden")
    pdf.bullet("Comandas abiertas: ordenes pendientes, en cocina o listas")
    pdf.bullet("Canceladas: ordenes canceladas del dia")
    pdf.ln(4)
    pdf.add_screenshot(f"{BASE}/guide_02_dashboard.png", "Panel de Reportes con KPIs del dia")
    pdf.ln(4)
    pdf.section_text(
        "Los reportes tienen 5 vistas: Financiero, Diario, Semanal, Mensual y Menu Engineering. "
        "La seccion 'Ingresos Reales' muestra un grafico de tendencia y 'Top Productos de Hoy' "
        "te indica cuales son los platos mas vendidos."
    )

    # ── 3. COPILOTO ADMIN ──
    pdf.add_page()
    pdf.chapter_title("3. Copiloto Admin (Sudamérica AI)")
    pdf.section_text(
        "Sudamérica AI es tu copiloto administrativo inteligente. Es un chat donde puedes "
        "gestionar tu restaurante con lenguaje natural. Ejemplos de lo que puedes pedirle:"
    )
    pdf.bullet("'Como van las ventas hoy?' - consulta ingresos y metricas en tiempo real")
    pdf.bullet("'Sube el precio de la pizza margarita a $12.000' - modifica precios al instante")
    pdf.bullet("'Que plato se vende mas?' - analisis de productos mas populares")
    pdf.bullet("'Desactiva el plato del dia' - cambia disponibilidad de productos")
    pdf.bullet("'Crea 5 mesas para el salon' - administra mesas")
    pdf.bullet("'Hay mesa libre para 4 personas manana a las 20:00?' - consulta disponibilidad")
    pdf.bullet("'Reserva para Juan Perez, 6 personas, sabado a las 21:00' - crea reservas")
    pdf.ln(4)
    pdf.add_screenshot(f"{BASE}/guide_03_copiloto_admin.png", "Chat con Sudamérica AI - Copiloto Administrativo")
    pdf.ln(4)
    pdf.section_text(
        "Tambien puedes adjuntar imagenes de tu carta/menu para que la IA extraiga los platos "
        "y precios automaticamente, o subir archivos CSV con listas de productos."
    )

    # ── 4. CONVERSACIONES IA ──
    pdf.add_page()
    pdf.chapter_title("4. Conversaciones IA (Prospectos)")
    pdf.section_text(
        "Esta seccion muestra todas las conversaciones que tu agente de IA tiene con tus clientes "
        "a traves de WhatsApp y otros canales. Funciona como una bandeja de entrada inteligente."
    )
    pdf.bullet("Vista de conversaciones: lista de chats con clientes, filtrable por canal")
    pdf.bullet("IA Auto: toggle para activar/desactivar respuestas automaticas de la IA")
    pdf.bullet("Outbound: toggle para mensajes salientes proactivos")
    pdf.bullet("Historial completo de cada conversacion con el cliente")
    pdf.ln(4)
    pdf.add_screenshot(f"{BASE}/guide_04_conversaciones.png", "Bandeja de Conversaciones IA")
    pdf.ln(4)
    pdf.section_text(
        "Cuando la IA no esta segura de una respuesta (confianza menor al 85%), "
        "el mensaje se envia a la cola de revision humana para que tu o tu equipo lo aprueben."
    )

    # ── 5. RENDIMIENTO IA ──
    pdf.add_page()
    pdf.chapter_title("5. Rendimiento IA")
    pdf.section_text(
        "El panel de Rendimiento IA te muestra las metricas clave de tu agente de inteligencia artificial:"
    )
    pdf.bullet("Auto-Resolucion: porcentaje de conversaciones resueltas sin intervencion humana")
    pdf.bullet("Costo por Conversacion: cuanto cuesta cada interaccion en tokens de IA")
    pdf.bullet("Horas Ahorradas: tiempo que la IA te ahorra automatizando respuestas")
    pdf.bullet("ROI IA: retorno de inversion de la inteligencia artificial")
    pdf.ln(4)
    pdf.add_screenshot(f"{BASE}/guide_03_copiloto.png", "Panel de Rendimiento IA con metricas clave")
    pdf.ln(4)
    pdf.section_text(
        "Tambien incluye graficos de 'Distribucion IA vs Humano' (cuantas conversaciones maneja "
        "cada uno), 'Horas Atendidas por Semana', 'Victorias de la IA' (conversaciones resueltas "
        "fuera de horario) y la 'Cola de Revision Humana' con mensajes pendientes de aprobar."
    )

    # ── 6. CONFIGURACION IA ──
    pdf.add_page()
    pdf.chapter_title("6. Configuracion IA")
    pdf.section_text(
        "Aqui personalizas como tu agente de IA interactua con los clientes. "
        "La configuracion tiene 4 secciones:"
    )
    pdf.bullet("Personalidad: nombre del agente, instrucciones generales, reglas de disponibilidad")
    pdf.bullet("Conocimiento: base de datos de conocimiento que la IA consulta (FAQs, politicas)")
    pdf.bullet("Comportamiento: reglas de escalamiento, umbral de confianza, horarios")
    pdf.bullet("Probar IA: chatea con tu agente para verificar que responde correctamente")
    pdf.ln(4)
    pdf.add_screenshot(f"{BASE}/guide_05_config_ia.png", "Configuracion de la identidad y personalidad del agente IA")
    pdf.ln(4)
    pdf.section_text(
        "En 'Identidad del Agente' defines el nombre (ej: Sofia, ChefIA) y las instrucciones "
        "de personalidad. En 'Disponibilidad y Sustituciones' configuras que hacer cuando un plato "
        "no esta disponible (ej: 'Si no hay Coca-Cola, ofrecer Pepsi')."
    )

    # ── 7. COMANDAS / KDS ──
    pdf.add_page()
    pdf.chapter_title("7. Cocina - KDS (Comandas)")
    pdf.section_text(
        "El KDS (Kitchen Display System) es la pantalla de cocina en tiempo real. "
        "Muestra las ordenes organizadas en 3 columnas:"
    )
    pdf.bullet("PENDIENTE (rojo): ordenes recien recibidas esperando preparacion")
    pdf.bullet("EN COCINA (naranja): ordenes que ya se estan preparando")
    pdf.bullet("LISTO (verde): ordenes terminadas listas para entregar")
    pdf.ln(4)
    pdf.add_screenshot(f"{BASE}/guide_06_comandas.png", "Sistema KDS - Vista de cocina en tiempo real")
    pdf.ln(4)
    pdf.section_text(
        "La conexion es EN VIVO via WebSocket - las comandas aparecen instantaneamente "
        "cuando un cliente hace un pedido. El indicador '0 ACTIVAS' muestra el total de "
        "ordenes en proceso. Puedes mover comandas entre columnas con un clic."
    )

    # ── 8. MESAS ──
    pdf.add_page()
    pdf.chapter_title("8. Mesas del Restaurante")
    pdf.section_text(
        "Administra las mesas de cada sucursal de tu restaurante. Para cada mesa puedes definir:"
    )
    pdf.bullet("Numero de mesa y nombre opcional")
    pdf.bullet("Capacidad (numero de personas)")
    pdf.bullet("Sucursal a la que pertenece")
    pdf.bullet("Codigo QR unico para que los clientes escaneen y hagan pedidos")
    pdf.ln(4)
    pdf.add_screenshot(f"{BASE}/guide_07_mesas.png", "Gestion de mesas por sucursal")
    pdf.ln(4)
    pdf.section_text(
        "Cada sucursal muestra sus mesas por separado. Puedes agregar mesas con '+ Agregar Mesa', "
        "editarlas o eliminarlas. El codigo QR permite a los clientes acceder al menu digital "
        "y hacer pedidos desde su celular."
    )

    # ── 9. RESERVACIONES ──
    pdf.add_page()
    pdf.chapter_title("9. Reservaciones")
    pdf.section_text(
        "Gestiona las reservas de tu restaurante. Puedes:"
    )
    pdf.bullet("Ver todas las reservaciones con filtro por fecha y estado")
    pdf.bullet("Filtrar por estado: Pendiente, Confirmada, Cancelada")
    pdf.bullet("Los clientes tambien pueden reservar hablando con la IA por WhatsApp")
    pdf.bullet("La IA verifica automaticamente la disponibilidad de mesas antes de confirmar")
    pdf.ln(4)
    pdf.add_screenshot(f"{BASE}/guide_08_reservaciones.png", "Panel de reservaciones con filtros")
    pdf.ln(4)
    pdf.section_text(
        "Las reservaciones se integran con el sistema de mesas - cuando un cliente pide "
        "una reserva por WhatsApp, la IA consulta las mesas disponibles y confirma automaticamente."
    )

    # ── 10. CARTA Y MENU ──
    pdf.add_page()
    pdf.chapter_title("10. Carta y Menu")
    pdf.section_text(
        "Administra tu carta digital completa. La seccion tiene dos pestanas:"
    )
    pdf.bullet("Platos: todos tus productos con precio, descripcion y disponibilidad")
    pdf.bullet("Modificadores: opciones extra como tamano, extras, ingredientes")
    pdf.ln(4)
    pdf.section_text("Para agregar productos tienes dos opciones:")
    pdf.bullet("'+ Nuevo Plato': crea un producto manualmente con nombre, precio, categoria")
    pdf.bullet("'Importar Menu': sube una imagen o PDF de tu carta y la IA extrae los platos automaticamente")
    pdf.ln(4)
    pdf.add_screenshot(f"{BASE}/guide_09_carta.png", "Gestion de Carta y Menu digital")
    pdf.ln(4)
    pdf.section_text(
        "Tambien puedes pedirle al Copiloto Admin que cree productos por ti. "
        "Por ejemplo: 'Crea una seccion Bebestibles con Coca-Cola a $1.200 y Jugo a $2.000'."
    )

    # ── 11. CLIENTES ──
    pdf.add_page()
    pdf.chapter_title("11. Clientes")
    pdf.section_text(
        "Vista completa de tus clientes/leads con dos modos de visualizacion:"
    )
    pdf.bullet("Vista CRM: tabla con datos detallados de cada cliente")
    pdf.bullet("Vista Clientes: vista simplificada para consulta rapida")
    pdf.ln(4)
    pdf.section_text("Para cada cliente puedes ver:")
    pdf.bullet("Nombre, canal de contacto (WhatsApp, Instagram, Web, etc.)")
    pdf.bullet("Estado del lead: Nuevo, Contactado, En Proceso, Convertido, Descartado")
    pdf.bullet("Valor estimado del cliente")
    pdf.bullet("Score IA: puntuacion de la inteligencia artificial sobre la probabilidad de compra")
    pdf.bullet("Fecha de creacion")
    pdf.ln(4)
    pdf.add_screenshot(f"{BASE}/guide_10_clientes.png", "CRM de clientes con filtros y Score IA")
    pdf.ln(4)
    pdf.section_text(
        "Usa los filtros de busqueda, estado y canal para encontrar clientes rapidamente. "
        "Con '+ Nuevo Cliente' puedes registrar clientes manualmente."
    )

    # ── 12. EQUIPO ──
    pdf.add_page()
    pdf.chapter_title("12. Equipo")
    pdf.section_text(
        "Administra los miembros de tu equipo y sus roles:"
    )
    pdf.bullet("SUPER ADMIN: acceso total a todas las funciones")
    pdf.bullet("ADMIN: gestion completa del restaurante")
    pdf.bullet("ASESOR: atencion a clientes y gestion de pedidos")
    pdf.bullet("VIEWER: solo lectura, puede ver reportes y metricas")
    pdf.ln(4)
    pdf.add_screenshot(f"{BASE}/guide_11_equipo.png", "Gestion de equipo con roles y ranking")
    pdf.ln(4)
    pdf.section_text(
        "La seccion incluye un Ranking del Equipo que muestra el desempeno de cada asesor "
        "(ventas realizadas e ingresos generados). Puedes invitar nuevos usuarios con "
        "'Invitar Usuario' y asignarles un rol y sucursal especifica."
    )

    # ── 13. CONFIGURACION ──
    pdf.add_page()
    pdf.chapter_title("13. Configuracion del Restaurante")
    pdf.section_text(
        "Configura los datos generales de tu restaurante:"
    )
    pdf.bullet("Nombre del restaurante")
    pdf.bullet("Tipo de cocina (italiana, japonesa, peruana, etc.)")
    pdf.bullet("Modalidad de atencion: Mesa, Delivery, Takeaway o combinaciones")
    pdf.bullet("Horario de atencion")
    pdf.bullet("Direccion y telefono")
    pdf.bullet("Descripcion para la IA")
    pdf.ln(4)
    pdf.add_screenshot(f"{BASE}/guide_12_configuracion.png", "Configuracion general del restaurante y sucursales")
    pdf.ln(4)
    pdf.section_text(
        "En la seccion 'Sucursales' puedes crear multiples locales, cada uno con su propia "
        "direccion y telefono. La sucursal marcada como 'PRINCIPAL' es la predeterminada. "
        "Puedes editar o eliminar sucursales segun necesites."
    )

    # ── FINAL PAGE ──
    pdf.add_page()
    pdf.ln(40)
    pdf.set_font("Helvetica", "B", 24)
    pdf.set_text_color(76, 110, 245)
    pdf.cell(0, 14, "Necesitas ayuda?", align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(10)
    pdf.set_font("Helvetica", "", 13)
    pdf.set_text_color(60, 60, 60)
    pdf.cell(0, 8, "Habla con Sudamérica AI desde el Copiloto Admin", align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.cell(0, 8, "o escribenos a soporte@sudamerica.ai", align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(20)
    pdf.set_font("Helvetica", "I", 10)
    pdf.set_text_color(130, 130, 130)
    pdf.cell(0, 8, "Sudamérica AI - Gastronomia Inteligente", align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.cell(0, 8, "Sudamérica AI - 2026", align="C", new_x="LMARGIN", new_y="NEXT")

    pdf.output(OUTPUT)
    print(f"PDF generado: {OUTPUT}")
    print(f"Paginas: {pdf.page_no()}")


if __name__ == "__main__":
    build_pdf()
