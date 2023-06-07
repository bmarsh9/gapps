from jinja2 import Environment, FileSystemLoader
from weasyprint import HTML, CSS
from flask import current_app
import arrow
import uuid
import os

class Report:
    def __init__(self):
        pass

    def base_config(self, project):
        config = current_app.config
        data = {
            "project_name": project.name,
            "app_name": config["APP_NAME"],
            "doc_url": config["DOC_LINK"],
            "console_url": config["CONSOLE_LINK"],
            "company": project.tenant.name,
            "contact_email": project.tenant.contact_email,
            "date": arrow.now().strftime("%d %B, %Y"),
            "report_title":"Compliance Report"
        }
        return data

    def project_data(self, project):
        return project.as_dict(with_controls=True)

    def generate(self, project, data=[], html_template="report.html",css_template="report.css"):
        """
        generates PDF report for project
        """
        config = self.base_config(project)
        config["data"] = self.project_data(project)

        env = Environment( loader = FileSystemLoader("app/templates/reports") )
        template = env.get_template(html_template)

        filebase = uuid.uuid4().hex
        generated_html = f"app/files/reports/{filebase}.html"
        with open(generated_html, 'w') as fh:
            fh.write(template.render(**config))

        filepath = f"app/files/reports/{filebase}.pdf"
        HTML(generated_html).write_pdf(filepath, stylesheets=[CSS(filename=f'app/static/css/{css_template}')])

        # remove generated html file
        if os.path.isfile(generated_html):
            os.remove(generated_html)
        return f"{filebase}.pdf"
