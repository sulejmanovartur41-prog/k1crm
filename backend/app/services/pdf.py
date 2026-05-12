import logging
import os
from datetime import datetime

from jinja2 import Environment, FileSystemLoader, select_autoescape

from app.config import settings

logger = logging.getLogger(__name__)

_template_dir = os.path.join(os.path.dirname(__file__), "..", "templates")
# autoescape — чтобы имена и паспортные данные не ломали HTML/PDF.
_jinja_env = Environment(
    loader=FileSystemLoader(_template_dir),
    autoescape=select_autoescape(["html", "xml"]),
)


async def generate_contract_pdf(client, contract) -> str:
    """Сгенерировать PDF договора.

    В prod-окружении WeasyPrint обязателен — ImportError превращается в RuntimeError,
    чтобы система не «молча» сохраняла HTML вместо подписываемого PDF.
    В dev — допустимо сохранить HTML как fallback, для удобства локальной отладки.
    """
    template = _jinja_env.get_template("contract.html")
    html_content = template.render(
        parent_name=client.parent_name,
        child_name=client.child_name,
        child_birth_date=client.child_birth_date.strftime("%d.%m.%Y"),
        amount=f"{contract.amount:,.0f}",
        date=datetime.now().strftime("%d.%m.%Y"),
        lesson_schedule="по расписанию",
    )

    output_dir = os.path.join(settings.storage_path, "contracts", str(client.id))
    os.makedirs(output_dir, exist_ok=True)

    date_str = datetime.now().strftime("%Y%m%d")
    pdf_path = os.path.join(output_dir, f"{date_str}_contract.pdf")

    try:
        from weasyprint import HTML
        HTML(string=html_content).write_pdf(pdf_path)
        logger.info("PDF generated: %s", pdf_path)
        return pdf_path
    except ImportError as e:
        if settings.environment != "dev":
            logger.error("WeasyPrint missing in prod — refusing to fall back to HTML")
            raise RuntimeError("WeasyPrint не установлен — PDF не сгенерирован") from e
        # dev only — fallback в HTML для удобства локальной разработки.
        html_path = pdf_path.replace(".pdf", ".html")
        with open(html_path, "w", encoding="utf-8") as f:
            f.write(html_content)
        logger.warning("WeasyPrint unavailable (dev), saved HTML: %s", html_path)
        return html_path
