from flask import Flask, request, send_file
from flask_cors import CORS
import os
import subprocess
import uuid
import re
import io
import logging

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)

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

    # Read the template content
    try:
        with open(tex_template_path, "r") as f:
            tex_content = f.read()
            logger.debug(f"Template content length: {len(tex_content)}")
    except Exception as e:
        logger.error(f"Error reading template: {str(e)}")
        return {"error": f"Could not read template file: {str(e)}"}, 500

    # Replace LaTeX \newcommand variables dynamically
    for key, value in data.items():
        # Escape special LaTeX characters
        value = str(value).replace('&', '\\&').replace('%', '\\%').replace('$', '\\$')
        value = value.replace('_', '\\_').replace('#', '\\#').replace('^', '\\^{}')
        pattern = re.compile(rf"(\\newcommand{{\\{key}}}{{)(.*?)}}")
        tex_content = pattern.sub(lambda m: f"{m.group(1)}{value}", tex_content)

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
                for line in result.stderr.splitlines():
                    logger.error(line)
                return {"error": f"PDF generation failed: {result.stderr}"}, 500
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