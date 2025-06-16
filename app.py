from flask import Flask, request, send_file
import os
import subprocess
import uuid
import re
import io

app = Flask(__name__)

@app.route("/generate", methods=["POST"])
def generate_pdf():
    data = request.json
    tex_template_path = "templates/report.tex"
    
    # Get current working directory
    cwd = os.getcwd()
    print(f"Current working directory: {cwd}")
    
    print(f"Template path (absolute): {os.path.abspath(tex_template_path)}")
    print(f"Template exists: {os.path.exists(tex_template_path)}")

    # Create a unique temp filename
    temp_id = str(uuid.uuid4())
    temp_tex_file = f"{temp_id}.tex"
    temp_pdf_file = f"{temp_id}.pdf"
    
    print(f"Temp files (absolute paths):")
    print(f"  TEX: {os.path.abspath(temp_tex_file)}")
    print(f"  PDF: {os.path.abspath(temp_pdf_file)}")

    # Read the template content
    try:
        with open(tex_template_path, "r") as f:
            tex_content = f.read()
            print(f"Template content length: {len(tex_content)}")
    except Exception as e:
        print(f"Error reading template: {str(e)}")
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
        print(f"Wrote temp tex file: {temp_tex_file}")
        print(f"Temp file exists: {os.path.exists(temp_tex_file)}")
    except Exception as e:
        print(f"Error writing temp file: {str(e)}")
        return {"error": f"Could not write temporary file: {str(e)}"}, 500

    try:
        # Run pdflatex twice to ensure proper PDF generation
        for i in range(2):
            result = subprocess.run(
                ["/Library/TeX/texbin/pdflatex", "-interaction=nonstopmode", temp_tex_file],
                capture_output=True,
                text=True
            )
            if result.returncode != 0:
                print(f"LaTeX compilation error (run {i+1}):")
                print(result.stderr)
                return {"error": f"PDF generation failed: {result.stderr}"}, 500
            print(f"LaTeX compilation output (run {i+1}):")
            print(result.stdout)

        if not os.path.exists(temp_pdf_file):
            print("PDF file was not created after compilation")
            return {"error": "PDF file was not created"}, 500

        print(f"PDF file exists: {os.path.exists(temp_pdf_file)}")
        print(f"PDF file size: {os.path.getsize(temp_pdf_file)} bytes")

        # Clean up temporary files except PDF
        for ext in ["tex", "log", "aux"]:
            temp_file = f"{temp_id}.{ext}"
            if os.path.exists(temp_file):
                os.remove(temp_file)

        # Return the PDF as a download
        response = send_file(
            temp_pdf_file,
            as_attachment=True,
            download_name=f"report_{temp_id}.pdf",
            mimetype='application/pdf'
        )

        # Clean up PDF file after sending
        @response.call_on_close
        def cleanup():
            if os.path.exists(temp_pdf_file):
                os.remove(temp_pdf_file)

        return response
    except subprocess.CalledProcessError as e:
        print(f"Subprocess error: {str(e)}")
        return {"error": str(e)}, 500
    except Exception as e:
        print(f"Unexpected error: {str(e)}")
        return {"error": str(e)}, 500

if __name__ == "__main__":
    app.run(debug=True, port=5000)
