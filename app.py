from flask import Flask, request, send_file
from flask_cors import CORS
import os
import subprocess
import uuid
import re
import io
import logging
import shutil

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app, origins=["https://vertekglobal.com"])  # Explicitly allow vertekglobal.com

@app.route("/generate", methods=["POST"])
def generate_pdf():
    data = request.json
    tex_template_path = "templates/report.tex"
    
    # Get current working directory
    cwd = os.getcwd()
    logger.debug(f"Current working directory: {cwd}")
    
    logger.debug(f"Template path (absolute): {os.path.abspath(tex_template_path)}")
    logger.debug(f"Template exists: {os.path.exists(tex_template_path)}")

    # Create a unique temp filename
    temp_id = str(uuid.uuid4())
    temp_tex_file = f"{temp_id}.tex"
    temp_pdf_file = f"{temp_id}.pdf"
    
    logger.debug(f"Temp files (absolute paths):")
    logger.debug(f"  TEX: {os.path.abspath(temp_tex_file)}")
    logger.debug(f"  PDF: {os.path.abspath(temp_pdf_file)}")

    # Check pdflatex availability
    if not shutil.which("pdflatex"):
        logger.error("pdflatex not found in PATH")
        return {"error": "pdflatex executable not found"}, 500

    # Read the template content
    try:
        with open(tex_template_path, "r") as f:
            tex_content = f.read()
            logger.debug(f"Template content length: {len(tex_content)}")
    except Exception as e:
        logger.error(f"Error reading template: {str(e)}")
        return {"error": f"Could not read template file: {str(e)}"}, 500

    # Log received data for debugging
    logger.debug(f"Received data: {data}")

    # Mapping JSON keys to LaTeX commands
    latex_mapping = {
        "firstName": "firstname",
        "lastName": "lastname",
        "company": "prospectname",
        "email": "email",
        "phone": "phone",
        "website": "website",
        "receptionists": "numreceptionists",
        "salary": "receptionistcost",
        "calls": "calls"
    }

    # Replace LaTeX \newcommand variables dynamically
    for json_key, value in data.items():
        if json_key in latex_mapping:
            latex_key = latex_mapping[json_key]
            # Escape special LaTeX characters
            value = str(value).replace('&', '\\&').replace('%', '\\%').replace('$', '\\$')
            value = value.replace('_', '\\_').replace('#', '\\#').replace('^', '\\^{}')
            pattern = re.compile(rf"(\\newcommand{{\\{latex_key}}}{{)(.*?)}}")
            original = pattern.search(tex_content)
            if original:
                logger.debug(f"Replacing \\{latex_key} from '{original.group(2)}' to '{value}'")
            tex_content = pattern.sub(lambda m: f"{m.group(1)}{value}", tex_content)
            # Replace command invocations in the document
            tex_content = tex_content.replace(f'\\{latex_key}', value)
    logger.debug(f"Modified template sample: {tex_content[:500]}...")

    # Write to a temporary .tex file
    try:
        with open(temp_tex_file, "w") as f:
            f.write(tex_content)
        logger.debug(f"Wrote temp tex file: {temp_tex_file}")
        logger.debug(f"Temp file exists: {os.path.exists(temp_tex_file)}")
    except Exception as e:
        logger.error(f"Error writing temp file: {str(e)}")
        return {"error": f"Could not write temporary file: {str(e)}"}, 500

    try:
        # Run pdflatex twice to ensure proper PDF generation
        for i in range(2):
            result = subprocess.run(
                ["pdflatex", "-interaction=nonstopmode", temp_tex_file],
                capture_output=True,
                text=True
            )
            if result.returncode != 0:
                logger.error(f"LaTeX compilation error (run {i+1}):")
                error_content = result.stderr if result.stderr else "No error details captured"
                for line in result.stderr.splitlines():
                    logger.error(line)
                return {"error": f"PDF generation failed. Error details: {error_content}"}, 500
            logger.debug(f"LaTeX compilation output (run {i+1}): {result.stdout}")

        if not os.path.exists(temp_pdf_file):
            logger.error("PDF file was not created after compilation")
            return {"error": "PDF file was not created"}, 500

        logger.debug(f"PDF file exists: {os.path.exists(temp_pdf_file)}")
        logger.debug(f"PDF file size: {os.path.getsize(temp_pdf_file)} bytes")

        # Clean up temporary files except PDF
        for ext in ["tex", "log", "aux"]:
            temp_file = f"{temp_id}.{ext}"
            if os.path.exists(temp_file):
                os.remove(temp_file)

        # Return the PDF as a download
        response = send_file(
            temp_pdf_file,
            as_attachment=True,
            download_name="AI_Cost_Savings_Report.pdf",
            mimetype='application/pdf'
        )

        # Clean up PDF file after sending
        @response.call_on_close
        def cleanup():
            if os.path.exists(temp_pdf_file):
                os.remove(temp_pdf_file)

        return response
    except subprocess.CalledProcessError as e:
        logger.error(f"Subprocess error: {str(e)}")
        return {"error": str(e)}, 500
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        return {"error": str(e)}, 500

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)