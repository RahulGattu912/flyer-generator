from flask import Flask, render_template, request, redirect, url_for, send_file
import os
import pandas as pd
from jinja2 import Environment, FileSystemLoader
from weasyprint import HTML, CSS
import uuid

app = Flask(__name__)
UPLOAD_FOLDER = 'uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER


def chunks(lst, n):
    for i in range(0, len(lst), n):
        yield lst[i:i + n]


def generate_flyer(csv_path, output_pdf_path):
    base_path = os.path.dirname(os.path.abspath(__file__))
    env = Environment(loader=FileSystemLoader(base_path))
    df = pd.read_csv(csv_path)
    if 'image_url' not in df.columns:
        df['image_url'] = 'https://images.unsplash.com/photo-1509042239860-f550ce710b93'

    items_data = df.to_dict('records')
    chunk_size = 4  # For Template A (4 items) and Template B (3 items)

    template_a = env.get_template('templates/flyer_template.html')
    template_b = env.get_template('templates/flyer_template_b.html')
    css_a = CSS(filename=os.path.join(base_path, 'static/css/flyer_style.css'))
    css_b = CSS(filename=os.path.join(base_path, 'static/css/flyer_style_b.css'))

    rendered_docs = []

    for i in range(0, len(items_data), chunk_size):
        chunk = items_data[i:i+chunk_size]
        if (i // chunk_size) % 2 == 0:
            template = env.get_template('templates/flyer_template.html')
            css_path = os.path.join(base_path, 'static/css/flyer_style.css')
        else:
            template = env.get_template('templates/flyer_template_b.html')
            css_path = os.path.join(base_path, 'static/css/flyer_style_b.css')

        html = template.render(items=chunk)
        css = CSS(filename=css_path)
        doc = HTML(string=html, base_url=base_path).render(stylesheets=[css])
        rendered_docs.append(doc)


    if not rendered_docs:
        return None

    merged_doc = rendered_docs[0]
    for doc in rendered_docs[1:]:
        merged_doc.pages.extend(doc.pages)

    merged_doc.write_pdf(output_pdf_path)
    return output_pdf_path


@app.route('/', methods=['GET', 'POST'])
def upload_file():
    if request.method == 'POST':
        file = request.files.get('file')
        if file and file.filename.endswith('.csv'):
            file_id = str(uuid.uuid4())
            filename = f"{file_id}.csv"
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(filepath)
            return redirect(url_for('loading', file_id=file_id))
    return render_template('upload.html')


@app.route('/loading/<file_id>')
def loading(file_id):
    return render_template('loading.html', file_id=file_id)


@app.route('/generate/<file_id>')
def generate(file_id):
    csv_path = os.path.join(app.config['UPLOAD_FOLDER'], f"{file_id}.csv")
    output_path = os.path.join(app.config['UPLOAD_FOLDER'], f"{file_id}.pdf")
    generate_flyer(csv_path, output_path)
    return redirect(url_for('download', file_id=file_id))


@app.route('/download/<file_id>')
def download(file_id):
    path = os.path.join(app.config['UPLOAD_FOLDER'], f"{file_id}.pdf")
    return render_template('download.html', file_id=file_id, pdf_path=url_for('send_pdf', file_id=file_id))


@app.route('/send_pdf/<file_id>')
def send_pdf(file_id):
    pdf_path = os.path.join(app.config['UPLOAD_FOLDER'], f"{file_id}.pdf")
    csv_path = os.path.join(app.config['UPLOAD_FOLDER'], f"{file_id}.csv")
    response = send_file(pdf_path, as_attachment=True, download_name='flyer.pdf')
    try:
        os.remove(pdf_path)
        os.remove(csv_path)
    except Exception as e:
        print(f"Cleanup error: {e}")
    return response


if __name__ == '__main__':
    app.run(debug=True)
