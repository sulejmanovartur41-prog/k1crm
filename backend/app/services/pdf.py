import logging
import os
from datetime import datetime

from jinja2 import Environment, FileSystemLoader

from app.config import settings

logger = logging.getLogger(__name__)

_template_dir = os.path.join(os.path.dirname(__file__), "..", "templates")
_jinja_env = Environment(loader=FileSystemLoader(_template_dir))


async def generate_contract_pdf(client, contract) -> str:
    """Render contract HTML and convert to PDF with WeasyPrint."""
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
    except ImportError:
        # WeasyPrint not available in dev — save HTML instead
        html_path = pdf_path.replace(".pdf", ".html")
        with open(html_path, "w", encoding="utf-8") as f:
            f.write(html_content)
        logger.warning("WeasyPrint unavailable, saved HTML: %s", html_path)
        return html_path

    return pdf_path
