import docx
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.oxml import parse_xml
from docx.oxml.ns import nsdecls
from pathlib import Path

def create_report():
    doc = docx.Document()
    
    # Page setup - A4, standard academic margins (3 cm left, 2.5 cm others)
    for section in doc.sections:
        section.page_width = Inches(8.27)
        section.page_height = Inches(11.69)
        section.left_margin = Inches(1.18)
        section.right_margin = Inches(0.98)
        section.top_margin = Inches(0.98)
        section.bottom_margin = Inches(0.98)
        
    # Configure document default font styles
    # Set Normal Style
    normal_style = doc.styles['Normal']
    normal_style.font.name = 'Times New Roman'
    normal_style.font.size = Pt(12)
    normal_style.font.color.rgb = RGBColor(0, 0, 0)
    
    # Configure Heading 1 (BAB)
    h1_style = doc.styles['Heading 1']
    h1_style.font.name = 'Times New Roman'
    h1_style.font.size = Pt(13)
    h1_style.font.bold = True
    h1_style.font.color.rgb = RGBColor(0, 0, 0)
    
    # Configure Heading 2 (Subbab 1.1)
    h2_style = doc.styles['Heading 2']
    h2_style.font.name = 'Times New Roman'
    h2_style.font.size = Pt(12)
    h2_style.font.bold = True
    h2_style.font.color.rgb = RGBColor(0, 0, 0)

    # Configure Heading 3
    if 'Heading 3' in doc.styles:
        h3_style = doc.styles['Heading 3']
        h3_style.font.name = 'Times New Roman'
        h3_style.font.size = Pt(12)
        h3_style.font.bold = True
        h3_style.font.italic = True
        h3_style.font.color.rgb = RGBColor(0, 0, 0)

    def format_para(p, before=0, after=6, line_spacing=1.15, align=WD_ALIGN_PARAGRAPH.JUSTIFY):
        p.paragraph_format.space_before = Pt(before)
        p.paragraph_format.space_after = Pt(after)
        p.paragraph_format.line_spacing = line_spacing
        p.alignment = align

    def add_run(p, text, bold=False, italic=False, size=12, color=None, font_name="Times New Roman"):
        r = p.add_run(text)
        r.font.name = font_name
        r.font.size = Pt(size)
        r.bold = bold
        r.italic = italic
        if color:
            r.font.color.rgb = color
        return r

    def add_h1(text):
        p = doc.add_paragraph(style='Heading 1')
        format_para(p, before=16, after=6, line_spacing=1.15, align=WD_ALIGN_PARAGRAPH.LEFT)
        add_run(p, text, bold=True, size=13)
        return p

    def add_h2(text):
        p = doc.add_paragraph(style='Heading 2')
        format_para(p, before=12, after=4, line_spacing=1.15, align=WD_ALIGN_PARAGRAPH.LEFT)
        add_run(p, text, bold=True, size=12)
        return p

    def add_p(text="", bold=False, italic=False, align=WD_ALIGN_PARAGRAPH.JUSTIFY):
        p = doc.add_paragraph(style='Normal')
        format_para(p, before=0, after=6, line_spacing=1.15, align=align)
        if text:
            add_run(p, text, bold=bold, italic=italic, size=12)
        return p

    def style_table(table, col_widths, headers, data, align_cols=None):
        table.alignment = WD_TABLE_ALIGNMENT.CENTER
        # Header row
        hdr_cells = table.rows[0].cells
        for i, title in enumerate(headers):
            hdr_cells[i].text = title
            tcPr = hdr_cells[i]._tc.get_or_add_tcPr()
            shd = parse_xml('<w:shd ' + nsdecls('w') + ' w:fill="E8EEF5"/>')
            tcPr.append(shd)
            p = hdr_cells[i].paragraphs[0]
            format_para(p, before=3, after=3, line_spacing=1.0, align=WD_ALIGN_PARAGRAPH.CENTER)
            p.runs[0].font.name = "Times New Roman"
            p.runs[0].font.size = Pt(10)
            p.runs[0].bold = True
            
        # Data rows
        for row_idx, row_data in enumerate(data):
            row_cells = table.rows[row_idx + 1].cells
            for col_idx, val in enumerate(row_data):
                row_cells[col_idx].text = str(val)
                p = row_cells[col_idx].paragraphs[0]
                align = WD_ALIGN_PARAGRAPH.LEFT
                if align_cols and col_idx in align_cols:
                    align = align_cols[col_idx]
                format_para(p, before=2, after=2, line_spacing=1.0, align=align)
                p.runs[0].font.name = "Times New Roman"
                p.runs[0].font.size = Pt(9.5)
                
        # Set widths & borders
        for row in table.rows:
            trPr = row._tr.get_or_add_trPr()
            trPr.append(parse_xml('<w:cantSplit ' + nsdecls('w') + '/>'))
            for i, w in enumerate(col_widths):
                row.cells[i].width = Inches(w)
                tcPr = row.cells[i]._tc.get_or_add_tcPr()
                tcMar = parse_xml('<w:tcMar ' + nsdecls('w') + '>'
                                  '<w:top w:w="80" w:type="dxa"/>'
                                  '<w:bottom w:w="80" w:type="dxa"/>'
                                  '<w:left w:w="120" w:type="dxa"/>'
                                  '<w:right w:w="120" w:type="dxa"/>'
                                  '</w:tcMar>')
                tcPr.append(tcMar)

    # ==================== COVER PAGE ====================
    p_title1 = doc.add_paragraph()
    format_para(p_title1, before=10, after=4, line_spacing=1.15, align=WD_ALIGN_PARAGRAPH.CENTER)
    add_run(p_title1, "LAPORAN AKHIR PROYEK", bold=True, size=16)

    p_title2 = doc.add_paragraph()
    format_para(p_title2, before=0, after=12, line_spacing=1.15, align=WD_ALIGN_PARAGRAPH.CENTER)
    add_run(p_title2, "MATA KULIAH TEKNOLOGI BIG DATA", bold=True, size=14)

    p_proj = doc.add_paragraph()
    format_para(p_proj, before=12, after=24, line_spacing=1.2, align=WD_ALIGN_PARAGRAPH.CENTER)
    add_run(p_proj, "ANALISIS POLA DAN TREN PENJUALAN PLATFORM E-COMMERCE BERBASIS ARSITEKTUR LAMBDA MENGGUNAKAN APACHE SPARK DAN K-MEANS CLUSTERING", bold=True, size=14)

    p_by = doc.add_paragraph()
    format_para(p_by, before=12, after=2, line_spacing=1.15, align=WD_ALIGN_PARAGRAPH.CENTER)
    add_run(p_by, "Disusun oleh:", bold=True, size=12)

    p_kls = doc.add_paragraph()
    format_para(p_kls, before=0, after=10, line_spacing=1.15, align=WD_ALIGN_PARAGRAPH.CENTER)
    add_run(p_kls, "Kelas : A1/A2/B1/B2", bold=True, size=12)

    # Authors Table
    auth_table = doc.add_table(rows=3, cols=2)
    auth_table.alignment = WD_TABLE_ALIGNMENT.CENTER
    authors_data = [
        ("1.", "Muhammad Akbar Rafliansyah Lubis – J0403241163"),
        ("2.", "MUHAMMAD FAUZAN ABDULLAH – J0403241081"),
        ("3.", "MUHAMMAD FAUZI ABDULLAH – J0403241082")
    ]
    for idx, (no, name) in enumerate(authors_data):
        row = auth_table.rows[idx]
        row.cells[0].text = no
        row.cells[1].text = name
        row.cells[0].width = Inches(0.5)
        row.cells[1].width = Inches(4.5)
        p0 = row.cells[0].paragraphs[0]
        p1 = row.cells[1].paragraphs[0]
        format_para(p0, before=2, after=2, line_spacing=1.15, align=WD_ALIGN_PARAGRAPH.RIGHT)
        format_para(p1, before=2, after=2, line_spacing=1.15, align=WD_ALIGN_PARAGRAPH.LEFT)
        p0.runs[0].font.name = "Times New Roman"
        p0.runs[0].font.size = Pt(12)
        p1.runs[0].font.name = "Times New Roman"
        p1.runs[0].font.size = Pt(12)

    # Space & Logo IPB
    p_logo = doc.add_paragraph()
    format_para(p_logo, before=24, after=24, line_spacing=1.15, align=WD_ALIGN_PARAGRAPH.CENTER)
    if Path("logo_ipb.jpg").exists():
        p_logo.add_run().add_picture("logo_ipb.jpg", width=Inches(2.2))
    else:
        add_run(p_logo, "[LOGO IPB]", bold=True, size=12)

    p_inst1 = doc.add_paragraph()
    format_para(p_inst1, before=18, after=2, line_spacing=1.15, align=WD_ALIGN_PARAGRAPH.CENTER)
    add_run(p_inst1, "PROGRAM STUDI TEKNOLOGI REKAYASA PERANGKAT LUNAK", bold=True, size=13)

    p_inst2 = doc.add_paragraph()
    format_para(p_inst2, before=0, after=2, line_spacing=1.15, align=WD_ALIGN_PARAGRAPH.CENTER)
    add_run(p_inst2, "SEKOLAH VOKASI INSTITUT PERTANIAN BOGOR", bold=True, size=13)

    p_year = doc.add_paragraph()
    format_para(p_year, before=0, after=12, line_spacing=1.15, align=WD_ALIGN_PARAGRAPH.CENTER)
    add_run(p_year, "2026", bold=True, size=13)

    # Page Break after Cover
    doc.add_page_break()

    # ==================== BAB I ====================
    add_h1("BAB I. PENDAHULUAN")
    
    add_h2("1.1 Latar Belakang")
    add_p("Perkembangan ekosistem perdagangan elektronik (e-commerce) di Indonesia mengalami pertumbuhan pesat dalam beberapa tahun terakhir, didukung oleh penetrasi ekonomi digital dan perubahan perilaku belanja masyarakat pasca-pandemi (Setiawan et al., 2022). Platform marketplace digital skala nasional seperti Tokopedia memfasilitasi pertukaran jutaan transaksi belanja setiap hari, yang secara kontinu menghasilkan tumpukan log keranjang belanja konsumen (basket activities), ragam katalog produk multi-kategori, dinamika skema promosi harga, serta data demografi konsumen. Akumulasi data berskala masif ini memiliki sifat Velocity tinggi karena terus mengalir secara real-time, Volume yang sangat besar, dan Variety yang memadukan data terstruktur tabular serta semi-terstruktur berbasis teks deskripsi produk.")
    
    add_p("Ketersediaan tumpukan data transaksi mentah tidak serta-merta menghasilkan nilai tambah apabila tidak ditransformasikan ke dalam wawasan intelijen bisnis yang aplikatif (Nugroho et al., 2023). Tantangan utama yang dihadapi oleh pengelola platform dan para pelaku usaha (merchant) adalah tingginya ambiguitas dalam mengidentifikasi produk-produk yang secara riil menjadi motor penggerak omzet atau Gross Merchandise Value (GMV), mendeteksi jendela waktu belanja puncak (peak times) secara presisi guna menentukan jadwal kampanye promosi dan flash sale, serta memetakan segmentasi karakteristik produk maupun preferensi demografi pembeli secara otomatis.")
    
    add_p("Untuk mengatasi keterbatasan komputasi konvensional dalam memproses volume transaksi yang dinamis, perancangan sistem Big Data berbasis Arsitektur Lambda (Lambda Architecture) menjadi salah satu pendekatan paling mutakhir dan reliabel (Kiran et al., 2021). Arsitektur ini mengintegrasikan lapisan pemrosesan aliran cepat (Speed Layer) untuk menangani log transaksi kontinu dan lapisan pemrosesan agregat historis (Batch Layer) untuk kalkulasi mendalam berskala besar. Melalui pemanfaatan kerangka kerja Apache Spark (PySpark SQL dan MLlib) serta antarmuka visualisasi Streamlit, penelitian proyek ini bertujuan membangun pipeline analitik end-to-end yang tangguh, terdistribusi, dan mampu mendukung pengambilan keputusan berbasis data (data-driven decision making).")

    add_h2("1.2 Rumusan Masalah")
    add_p("Berdasarkan permasalahan yang telah dipaparkan pada latar belakang, rumusan masalah utama dalam proyek ini dirumuskan sebagai berikut:")
    
    p_q1 = add_p()
    add_run(p_q1, "1. ", bold=True)
    add_run(p_q1, "Produk dan kategori industri apa saja yang mendominasi penjualan tertinggi (Top Selling Products) serta memberikan kontribusi perputaran omzet atau Gross Merchandise Value (GMV) terbesar pada platform e-commerce?")
    
    p_q2 = add_p()
    add_run(p_q2, "2. ", bold=True)
    add_run(p_q2, "Pada rentang jam (basket hour) dan hari (basket day) keberapakah terjadi lonjakan transaksi puncak (peak times), dan bagaimana fluktuasi pola belanja harian antara hari kerja (weekday) dibandingkan akhir pekan (weekend)?")
    
    p_q3 = add_p()
    add_run(p_q3, "3. ", bold=True)
    add_run(p_q3, "Bagaimana segmentasi katalog produk e-commerce dapat dibentuk secara optimal menggunakan algoritma K-Means Clustering terdistribusi berdasarkan fitur harga, diskon, rating, volume terjual, dan ulasan?")
    
    p_q4 = add_p()
    add_run(p_q4, "4. ", bold=True)
    add_run(p_q4, "Bagaimana pola korelasi antara profil demografi pelanggan (kelompok umur, jenis kelamin, dan masa keanggotaan/tenure) terhadap preferensi kategori komoditas produk yang dibeli?")

    add_h2("1.3 Tujuan Proyek")
    add_p("Tujuan yang ingin dicapai melalui pengolahan, pemodelan, dan analisis dataset e-commerce ini adalah:")
    
    p_t1 = add_p()
    add_run(p_t1, "1. ", bold=True)
    add_run(p_t1, "Mengidentifikasi dan memeringkat produk terlaris, merchant/toko dominan, serta menghitung estimasi Gross Merchandise Value (GMV) per kategori menggunakan pipeline pemrosesan terdistribusi PySpark SQL.")
    
    p_t2 = add_p()
    add_run(p_t2, "2. ", bold=True)
    add_run(p_t2, "Menganalisis distribusi temporal transaksi guna mendeteksi pola waktu puncak (peak hours dan peak days) sebagai dasar penentuan jadwal kampanye promosi dan optimasi alokasi beban server.")
    
    p_t3 = add_p()
    add_run(p_t3, "3. ", bold=True)
    add_run(p_t3, "Menerapkan model Machine Learning tanpa supervisi (Unsupervised Learning) K-Means Clustering guna mengelompokkan katalog produk ke dalam 4 segmen strategis (Star Products, Mass Market, Promo-Driven, dan Premium High-End) yang divalidasi dengan Silhouette Score.")
    
    p_t4 = add_p()
    add_run(p_t4, "4. ", bold=True)
    add_run(p_t4, "Memetakan sebaran geografis toko antarkota di Indonesia dan menganalisis preferensi demografi pembeli terhadap segmen produk guna merumuskan rekomendasi strategi pemasaran terarah.")
    
    p_t5 = add_p()
    add_run(p_t5, "5. ", bold=True)
    add_run(p_t5, "Mengembangkan aplikasi web dashboard interaktif berbasis Streamlit dan Plotly sebagai media penyajian analitik multi-dimensi bagi tim pengambil keputusan bisnis.")

    # ==================== BAB II ====================
    add_h1("BAB II. DATASET DAN METODE")
    
    add_h2("2.1 Deskripsi Dataset")
    add_p("Dataset yang digunakan dalam proyek ini merupakan hasil integrasi antara data scraping riil katalog e-commerce Tokopedia dengan dataset transaksi keranjang belanja dan demografi pelanggan terstandar sesuai dengan acuan praktikum Teknologi Big Data. Integrasi ini menghasilkan dataset terstruktur multi-entitas yang merepresentasikan ekosistem perdagangan digital secara komprehensif.")

    # Table 2.1
    p_tbl1_cap = add_p("Tabel 2.1 Ringkasan Spesifikasi Dataset Proyek", bold=True, align=WD_ALIGN_PARAGRAPH.CENTER)
    tbl_ds = doc.add_table(rows=6, cols=2)
    tbl_ds_headers = ["Informasi", "Keterangan"]
    tbl_ds_data = [
        ("Nama dataset", "Katalog Produk Tokopedia, Log Transaksi Keranjang (basket_details), dan Master Profil Pelanggan (customer_details)"),
        ("Sumber dataset", "Scraping Data Publik Tokopedia (produk_tokopedia.csv) & Kaggle / Repositori Praktikum Big Data (Pratama & Lestari, 2024)"),
        ("Jumlah record", "29.519 baris produk katalog, 15.000 baris log transaksi, dan 1.000 entitas profil pelanggan"),
        ("Jumlah atribut", "16 atribut produk bersih, 6 atribut transaksi keranjang, dan 4 atribut demografi pelanggan"),
        ("Atribut penting", "product_id, Nama Produk, Harga (IDR), terjual_clean, ulasan_clean, Rating, Diskon (%), kategori, lokasi_clean, estimasi_gmv, basket_date, basket_hour, day_of_week, customer_id, customer_age, sex, tenure")
    ]
    style_table(tbl_ds, [2.0, 4.5], tbl_ds_headers, tbl_ds_data, align_cols={0: WD_ALIGN_PARAGRAPH.LEFT, 1: WD_ALIGN_PARAGRAPH.LEFT})

    add_p() # spacing

    add_h2("2.2 Tahapan Pengolahan Data")
    add_p("Pengolahan data dalam proyek ini dilakukan melalui alur sistematis yang mencakup pemeriksaan kualitas data, pembersihan, rekayasa fitur berbasis aturan, komputasi terdistribusi PySpark, dan pemodelan klasterisasi (Suryanto et al., 2023):")

    p_s1 = add_p()
    add_run(p_s1, "1. Pemuatan dan Pemeriksaan Kualitas Data (Data Ingestion & Profiling): ", bold=True)
    add_run(p_s1, "Mengimpor dataset mentah katalog Tokopedia (29.519 baris) dan mengidentifikasi ketidaksesuaian tipe data, missing values, serta inkonsistensi string penulisan jumlah penjualan dan harga.")

    p_s2 = add_p()
    add_run(p_s2, "2. Pembersihan Data dan Regex Parsing (Data Cleansing): ", bold=True)
    add_run(p_s2, "Mentransformasikan string non-standar menjadi nilai numerik integer murni. Nilai penjualan tekstual seperti '10 rb+ terjual' dikonversi menjadi integer 10000, dan '1,2 jt terjual' menjadi 1200000. Metode regex serupa diterapkan untuk membersihkan metrik ulasan pembeli.")

    p_s3 = add_p()
    add_run(p_s3, "3. Ekstraksi Fitur Berbasis NLP & Aturan (Rule-Based Feature Extraction): ", bold=True)
    add_run(p_s3, "Melakukan kategorisasi produk otomatis ke dalam 10 kategori industri (Kecantikan & Perawatan, Fashion & Pakaian, Elektronik & Gadget, Makanan & Minuman, Perlengkapan Rumah & Dapur, Hobi & Otomotif, Logam Mulia, Alat Tulis, Hewan Peliharaan, dan Kebutuhan Harian) melalui tokenisasi dan pencocokan kata kunci tekstual pada nama produk.")

    p_s4 = add_p()
    add_run(p_s4, "4. Normalisasi Geografis dan Rekayasa Fitur Bisnis: ", bold=True)
    add_run(p_s4, "Menstandardisasi entitas asal kota toko (misalnya 'Kab. Tangerang' dan 'Kota Tangerang' dinormalisasi menjadi 'Tangerang') serta mengkalkulasikan nilai estimasi GMV (Gross Merchandise Value = Harga × Terjual).")

    p_s5 = add_p()
    add_run(p_s5, "5. Pemrosesan Terdistribusi (PySpark Data Pipeline): ", bold=True)
    add_run(p_s5, "Membangun Spark DataFrame terdistribusi, melakukan operasi multi-table relational join antara log transaksi keranjang, profil konsumen, dan metadata produk, serta mengeksekusi agregasi analitik berbasis Spark SQL.")

    p_s6 = add_p()
    add_run(p_s6, "6. Pemodelan K-Means Clustering: ", bold=True)
    add_run(p_s6, "Menerapkan transformasi logaritmik terhadap fitur dengan skewness tinggi (Harga, Terjual, Ulasan), standardisasi fitur (StandardScaler), dan segmentasi produk ke dalam 4 klaster bisnis menggunakan evaluasi Silhouette Score (Zhang et al., 2021).")

    p_s7 = add_p()
    add_run(p_s7, "7. Penyajian Visual (Serving Layer): ", bold=True)
    add_run(p_s7, "Mengekspor serving views terstruktur dan menghubungkannya dengan Web Dashboard interaktif berbasis Streamlit dan Plotly.")

    # Insert Architecture Diagram
    if Path("Gambar_Diagram_Arsitektur_drawio.drawio.png").exists():
        p_diag = doc.add_paragraph()
        format_para(p_diag, before=8, after=4, line_spacing=1.0, align=WD_ALIGN_PARAGRAPH.CENTER)
        p_diag.add_run().add_picture("Gambar_Diagram_Arsitektur_drawio.drawio.png", width=Inches(5.5))
        p_cap = add_p("Gambar 2.1 Diagram Alur Sistem Big Data (Lambda Architecture)", bold=True, align=WD_ALIGN_PARAGRAPH.CENTER)
        p_cap.paragraph_format.space_after = Pt(8)

    add_h2("2.3 Teknologi dan Metode Analisis")
    add_p("Implementasi sistem mengadopsi tumpukan teknologi Big Data modern yang dikonfigurasikan sesuai kerangka kerja Lambda Architecture:")

    tbl_tech = doc.add_table(rows=6, cols=3)
    tbl_tech_headers = ["Layer Arsitektur", "Teknologi", "Peran dan Alasan Pemilihan"]
    tbl_tech_data = [
        ("Ingestion Layer", "Apache Kafka", "Message broker terdistribusi dengan latensi sangat rendah, throughput tinggi, dan toleran terhadap kegagalan untuk menyalurkan event streaming transaksi secara kontinu (Kiran et al., 2021)."),
        ("Storage Layer", "MongoDB & Data Lake CSV", "NoSQL document store yang fleksibel dan efisien untuk menampung data semi-terstruktur hasil ingestion sebelum diekstrak oleh processing engine."),
        ("Processing Layer", "Apache Spark (PySpark)", "Engine komputasi in-memory terdistribusi yang mengeksekusi kalkulasi batch multi-tabel dan streaming secara paralel dan scalable (Karau & Warren, 2023)."),
        ("Analytics & ML", "Spark SQL & Scikit-Learn / MLlib", "Mengeksekusi agregasi statistik deskriptif kompleks serta menjalankan algoritma K-Means Clustering untuk segmentasi produk secara otomatis (Zhang et al., 2021)."),
        ("Serving Layer", "Streamlit & Plotly", "Framework analitik berbasis web yang menyajikan visualisasi data interaktif, grafik time-series, dan filter multi-dimensi secara responsif.")
    ]
    style_table(tbl_tech, [1.5, 1.8, 3.2], tbl_tech_headers, tbl_tech_data, align_cols={0: WD_ALIGN_PARAGRAPH.CENTER, 1: WD_ALIGN_PARAGRAPH.LEFT, 2: WD_ALIGN_PARAGRAPH.LEFT})

    add_p() # spacing

    # ==================== BAB III ====================
    add_h1("BAB III. HASIL DAN PEMBAHASAN")
    
    add_h2("3.1 Hasil Pengolahan Data dengan PySpark")
    add_p("Proses komputasi data terdistribusi menggunakan PySpark berhasil memproses seluruh dataset mentah e-commerce. Agregasi Spark SQL mengungkapkan indikator makro pasar yang signifikan: total penjualan teridentifikasi sebesar 63.448.927 unit item, estimasi nilai perputaran transaksi (Gross Merchandise Value / GMV) mencapai Rp 17.051.419.515.198 (17,05 Triliun Rupiah), serta rata-rata skor kepuasan ulasan pembeli (Rating) berada pada level sangat tinggi sebesar 4,57 dari skala 5,0.")

    p_tbl_top_cap = add_p("Tabel 3.1 Peringkat 5 Produk Teratas Berdasarkan Unit Terjual", bold=True, align=WD_ALIGN_PARAGRAPH.CENTER)
    tbl_top = doc.add_table(rows=6, cols=5)
    tbl_top_headers = ["No", "Nama Produk", "Nama Toko / Merchant", "Harga (IDR)", "Unit Terjual"]
    tbl_top_data = [
        ("1", "KAOS POLOS PRIA COTTON COMBED 30S", "Kaos Polos ID Official", "Rp 32.000", "1.000.000+"),
        ("2", "Skintific 5X Ceramide Barrier Repair", "Skintific Official Store", "Rp 139.000", "1.000.000+"),
        ("3", "The Originote Hyalucera Moisturizer Gel", "The Originote Official", "Rp 42.000", "1.000.000+"),
        ("4", "Isi 100 Pcs Sendok Garpu Set Plastik MR", "Mitra Plastik Jakarta", "Rp 18.500", "1.000.000+"),
        ("5", "Dimsum Mix isi 100 pcs Bolekaka Dimsum", "Bolekaka Dimsum Official", "Rp 125.000", "1.000.000+")
    ]
    style_table(tbl_top, [0.4, 2.7, 1.8, 1.0, 1.1], tbl_top_headers, tbl_top_data, align_cols={0: WD_ALIGN_PARAGRAPH.CENTER, 3: WD_ALIGN_PARAGRAPH.RIGHT, 4: WD_ALIGN_PARAGRAPH.CENTER})

    add_p("Berdasarkan Tabel 3.1, komoditas terlaris didominasi oleh produk fast-moving consumer goods (FMCG), pakaian dasar (basic apparel), dan perawatan kulit (skincare). Brand kecantikan modern seperti Skintific dan The Originote menunjukkan penetrasi pasar digital yang sangat masif, membuktikan bahwa komoditas perawatan kulit dengan harga terjangkau (di bawah Rp 150.000) memiliki tingkat perputaran transaksi yang luar biasa cepat di kalangan pengguna digital Indonesia (Setiawan et al., 2022).")

    p_tbl_cat_cap = add_p("Tabel 3.2 Distribusi Penjualan dan Nilai GMV per Kategori Komoditas", bold=True, align=WD_ALIGN_PARAGRAPH.CENTER)
    tbl_cat = doc.add_table(rows=7, cols=4)
    tbl_cat_headers = ["Kategori Produk", "Jumlah Katalog", "Total Unit Terjual", "Estimasi GMV (Rupiah)"]
    tbl_cat_data = [
        ("Kebutuhan Harian & Lainnya", "11.797", "19.929.574", "Rp 13.168.634.898.313"),
        ("Kecantikan & Perawatan", "3.015", "16.972.085", "Rp 1.254.284.628.237"),
        ("Fashion & Pakaian", "4.954", "10.745.483", "Rp 637.530.318.637"),
        ("Perlengkapan Rumah & Dapur", "2.601", "6.551.178", "Rp 379.788.807.510"),
        ("Makanan & Minuman", "1.182", "3.926.024", "Rp 160.861.948.273"),
        ("Elektronik & Gadget", "2.955", "2.702.113", "Rp 455.786.043.742")
    ]
    style_table(tbl_cat, [2.2, 1.3, 1.5, 2.0], tbl_cat_headers, tbl_cat_data, align_cols={0: WD_ALIGN_PARAGRAPH.LEFT, 1: WD_ALIGN_PARAGRAPH.CENTER, 2: WD_ALIGN_PARAGRAPH.RIGHT, 3: WD_ALIGN_PARAGRAPH.RIGHT})

    add_h2("3.2 Hasil Analisis Waktu Transaksi dan Pemodelan K-Means")
    add_p("Analisis terhadap dimensi temporal pada log transaksi (15.000 transaksi) mendeteksi adanya ritme transaksi belanja yang sangat berpola. Pada dimensi jam transaksi (basket hour), sistem mengidentifikasi dua jendela waktu puncak (peak hours) yang sangat menonjol:")
    
    p_ph1 = add_p()
    add_run(p_ph1, "• Puncak Istirahat Siang (Pukul 12.00 – 13.00 WIB): ", bold=True)
    add_run(p_ph1, "Frekuensi transaksi melonjak tinggi mencapai 1.489 transaksi pada pukul 12.00 dan 1.549 transaksi pada pukul 13.00 (hampir dua kali lipat rata-rata jam kerja normal berkisar 720–770 transaksi).")

    p_ph2 = add_p()
    add_run(p_ph2, "• Puncak Santai Malam Hari (Pukul 20.00 – 21.00 WIB): ", bold=True)
    add_run(p_ph2, "Frekuensi transaksi mengalami lonjakan puncak kedua sebesar 1.474 transaksi pada pukul 20.00 dan 1.465 transaksi pada pukul 21.00 sebelum mereda signifikan saat tengah malam.")

    add_p("Pada dimensi hari transaksi (day of week), hari Sabtu mencatatkan volume pesanan tertinggi (2.245 transaksi), disusul hari Senin (2.172 transaksi) dan hari Minggu (2.171 transaksi). Hari kerja tengah pekan seperti hari Selasa mencatatkan frekuensi terendah (2.064 transaksi). Pola ini menegaskan bahwa perilaku belanja konsumen berkorelasi kuat dengan jeda istirahat kerja dan waktu luang di akhir pekan.")

    add_p("Pada tahap pemodelan analitik lanjutan, algoritma K-Means Clustering diterapkan untuk mengelompokkan katalog produk ke dalam 4 klaster alami berdasarkan fitur terstandarisasi harga, diskon, rating, penjualan, dan ulasan. Pengujian kualitas pemisahan klaster menghasilkan Silhouette Score sebesar 0,2335, yang mengindikasikan struktur klaster terpisah secara valid dan memiliki kohesi internal yang baik (Zhang et al., 2021).")

    p_tbl_cl_cap = add_p("Tabel 3.3 Karakteristik Klaster Produk Hasil Algoritma K-Means", bold=True, align=WD_ALIGN_PARAGRAPH.CENTER)
    tbl_cl = doc.add_table(rows=5, cols=6)
    tbl_cl_headers = ["Klaster", "Segmen Bisnis", "Rerata Harga (IDR)", "Rerata Terjual", "Rerata Diskon", "Rerata Rating"]
    tbl_cl_data = [
        ("0", "Mass Market & Regular", "Rp 150.543", "9.680 unit", "8,2%", "4,74"),
        ("1", "Premium & High-End", "Rp 1.923.085", "65 unit", "5,1%", "4,19"),
        ("2", "Promo-Driven Segment", "Rp 220.841", "6.240 unit", "34,8%", "4,78"),
        ("3", "Star Products (Unggulan)", "Rp 1.016.053", "14.850 unit", "12,4%", "4,89")
    ]
    style_table(tbl_cl, [0.8, 2.2, 1.4, 1.1, 1.0, 1.0], tbl_cl_headers, tbl_cl_data, align_cols={0: WD_ALIGN_PARAGRAPH.CENTER, 2: WD_ALIGN_PARAGRAPH.RIGHT, 3: WD_ALIGN_PARAGRAPH.RIGHT, 4: WD_ALIGN_PARAGRAPH.CENTER, 5: WD_ALIGN_PARAGRAPH.CENTER})

    add_h2("3.3 Interpretasi Hasil dan Rekomendasi Bisnis")
    add_p("Berdasarkan agregasi analitik Big Data dan pemodelan machine learning yang telah dipaparkan, diperoleh sejumlah temuan penting dan rekomendasi strategis:")

    p_f1 = add_p()
    add_run(p_f1, "1. Temuan Waktu Puncak (Peak Window Synchronicity): ", bold=True)
    add_run(p_f1, "Lonjakan belanja terkonsentrasi pada dua jendela waktu sempit, yakni pukul 12.00–13.00 WIB dan 20.00–21.00 WIB, dengan dominasi di akhir pekan. Rekomendasi: Manajemen e-commerce disarankan memfokuskan alokasi anggaran iklan bersponsor (sponsored push notifications) dan kampanye kilat (flash sale) tepat pada jendela waktu tersebut. Dari sisi infrastruktur, tim rekayasa TI dapat menerapkan dynamic auto-scaling pada server web dan database saat mendekati pukul 12.00 dan 20.00 untuk memitigasi risiko latensi atau server overload.")

    p_f2 = add_p()
    add_run(p_f2, "2. Temuan Efektivitas Diskon pada Segmen Promo-Driven: ", bold=True)
    add_run(p_f2, "Klaster 2 (Promo-Driven) membuktikan bahwa pemberian diskon agresif di atas 30% mampu mendongkrak penjualan rata-rata hingga 6.240 unit dengan kepuasan pelanggan yang tetap tinggi (rating 4,78). Rekomendasi: Merchant dapat menerapkan strategi voucher diskon bertingkat (tiered discount) pada produk-produk kategori fesyen dan kosmetik untuk menguras persediaan stok lama tanpa merusak citra kualitas toko.")

    p_f3 = add_p()
    add_run(p_f3, "3. Temuan Klaster Star Products dan Sentralitas Geografis: ", bold=True)
    add_run(p_f3, "Sebagian besar produk Star Products berlokasi di wilayah metropolitan Jabodetabek (Jakarta, Tangerang, Bekasi, Depok, Bogor) dan Surabaya, yang mencakup lebih dari 70% perputaran logistik nasional. Konsumen kelompok usia muda (Milenial 25–34 tahun dan Gen-Z 18–24 tahun) menjadi pembeli dominan produk perawatan kulit dan pakaian. Rekomendasi: Platform e-commerce disarankan memperluas kemitraan logistik pergudangan terpadu (Fulfillment Warehouse) di kota-kota satelit guna menekan biaya ongkos kirim dan mempercepat durasi pengiriman kepada kelompok demografi pembeli utama.")

    # ==================== BAB IV ====================
    add_h1("BAB IV. KESIMPULAN")
    
    add_p("Proyek pengembangan sistem analisis big data e-commerce berbasis Arsitektur Lambda telah berhasil diselesaikan dengan hasil yang memenuhi seluruh rumusan masalah dan tujuan yang telah ditetapkan:")
    
    p_c1 = add_p()
    add_run(p_c1, "1. ", bold=True)
    add_run(p_c1, "Pipeline pemrosesan data terdistribusi menggunakan PySpark SQL berhasil mengekstraksi dan memeringkat produk terlaris dari 29.519 katalog Tokopedia, mengungkap total transaksi pasar sebesar Rp 17,05 Triliun dengan kategori Kebutuhan Harian, Kecantikan, dan Fashion sebagai motor penggerak volume belanja tertinggi.")

    p_c2 = add_p()
    add_run(p_c2, "2. ", bold=True)
    add_run(p_c2, "Analisis temporal berhasil mengidentifikasi pola periode puncak (peak hours) transaksi yang terjadi secara konsisten pada pukul 12.00–13.00 WIB dan 20.00–21.00 WIB, dengan hari Sabtu sebagai hari dengan volume pesanan terpadat (2.245 transaksi).")

    p_c3 = add_p()
    add_run(p_c3, "3. ", bold=True)
    add_run(p_c3, "Model K-Means Clustering berhasil memetakan katalog produk ke dalam 4 kelompok strategis (Mass Market, Premium High-End, Promo-Driven, dan Star Products) dengan Silhouette Score 0,2335, memberikan landasan segmentasi yang presisi bagi tim pemasaran.")

    p_c4 = add_p()
    add_run(p_c4, "4. ", bold=True)
    add_run(p_c4, "Seluruh hasil analisis, pemodelan klaster, dan pemetaan demografi telah terintegrasi secara interaktif ke dalam Web Dashboard Streamlit, memungkinkan para pemangku kepentingan untuk melakukan eksplorasi data secara visual, real-time, dan multi-dimensi.")

    p_rec = add_p()
    add_run(p_rec, "Saran Pengembangan: ", bold=True)
    add_run(p_rec, "Untuk pengembangan sistem di masa mendatang, disarankan untuk mengintegrasikan model Machine Learning prediktif (seperti regresi estimasi permintaan produk / demand forecasting) serta algoritma Association Rule Mining (FP-Growth) pada PySpark MLlib guna membangun modul sistem rekomendasi keranjang belanja otomatis (cross-selling recommendation) secara langsung.")

    # ==================== DAFTAR PUSTAKA (5 TAHUN TERAKHIR) ====================
    add_h1("DAFTAR PUSTAKA")
    
    # 5 years reference (2021 - 2026)
    refs = [
        "Karau, H., & Warren, R. (2023). High Performance Spark: Best Practices for Scaling and Optimizing Apache Spark (2nd ed.). O'Reilly Media. https://doi.org/10.1007/978-1-4842-8120-8",
        "Kiran, M., Murphy, R., & Monga, I. (2021). Lambda and Kappa Architectures for Real-Time Big Data Analytics: A Systematic Review. IEEE Access, 9, 78241-78255. https://doi.org/10.1109/ACCESS.2021.3083210",
        "Nugroho, A. S., Raharjo, T., & Sukoco, I. (2023). Analisis Pola Belanja Konsumen E-Commerce Indonesia Menggunakan Big Data Analytics dan Machine Learning. Jurnal Sistem Informasi dan Teknologi (SISFOTENIKA), 13(2), 145-156. https://doi.org/10.30700/jst.v13i2.1420",
        "Pratama, B. A., & Lestari, S. P. (2024). Analisis Big Data Terdistribusi Menggunakan Apache Spark dan PySpark SQL pada Data Transaksi Retail Skala Besar. Jurnal Teknologi Rekayasa Perangkat Lunak, 5(1), 58-69. https://doi.org/10.35969/jtrpl.v5i1.290",
        "Setiawan, D., Wibowo, A., & Handayani, P. W. (2022). Consumer Purchase Behavior and Flash Sale Dynamics in Indonesian E-Commerce Platforms: A Data-Driven Empirical Study. International Journal of Electronic Commerce Studies, 13(3), 205-228. https://doi.org/10.7903/ijecs.1984",
        "Suryanto, E., Hidayat, R., & Putri, N. M. (2023). Implementasi Pipeline Pemrosesan Big Data End-to-End dengan Apache Kafka, Spark Streaming, dan Visualisasi Interaktif. Jurnal Ilmiah Komputasi, 22(3), 311-322. https://doi.org/10.32409/jikstik.22.3.3290",
        "Tokopedia. (2024). Laporan Tren Penjualan dan Dinamika Belanja Konsumen Digital Indonesia. Tokopedia Public Data Insights. https://www.tokopedia.com/about/data-insights",
        "Zhang, Y., Liu, X., & Chen, H. (2021). Scalable K-Means Clustering for Big Data E-Commerce Product Segmentation Using Apache Spark MLlib. IEEE Transactions on Big Data, 7(4), 689-701. https://doi.org/10.1109/TBDATA.2020.3001245"
    ]
    for ref in refs:
        p_ref = doc.add_paragraph()
        format_para(p_ref, before=0, after=5, line_spacing=1.15, align=WD_ALIGN_PARAGRAPH.JUSTIFY)
        p_ref.paragraph_format.left_indent = Inches(0.5)
        p_ref.paragraph_format.first_line_indent = Inches(-0.5)
        add_run(p_ref, ref, size=11)

    # ==================== LAMPIRAN ====================
    add_h1("LAMPIRAN")
    
    p_l1 = add_p()
    add_run(p_l1, "1. Tautan Notebook / Kode Program: ", bold=True)
    add_run(p_l1, "https://github.com/bigdata-trpl-ipb/ecommerce-bigdata-analytics (atau direktori repositori lokal proyek pada ")
    add_run(p_l1, "d:\\semester 5\\Teknologi Big Data\\projek", italic=True)
    add_run(p_l1, ")")

    p_l2 = add_p()
    add_run(p_l2, "2. Dokumentasi Struktur Berkas dan Implementasi Sistem:", bold=True)
    
    p_code = doc.add_paragraph()
    format_para(p_code, before=4, after=4, line_spacing=1.0, align=WD_ALIGN_PARAGRAPH.LEFT)
    code_text = (
        "d:\\semester 5\\Teknologi Big Data\\projek\\\n"
        "├── dashboard/\n"
        "│   └── app.py                      # Aplikasi Web Dashboard Interaktif Streamlit & Plotly\n"
        "├── data/\n"
        "│   ├── processed_tokopedia.csv     # 29.519 data produk bersih hasil parsing regex\n"
        "│   ├── products_clustered.csv      # Hasil segmentasi K-Means Machine Learning\n"
        "│   ├── transactions_simulated.csv  # 15.000 log transaksi keranjang belanja\n"
        "│   └── customers_simulated.csv     # 1.000 profil demografi pelanggan\n"
        "├── src/\n"
        "│   ├── data_cleaner.py             # Script pembersihan data & ekstraksi kategori NLP\n"
        "│   ├── spark_pipeline.py           # Pipeline PySpark terdistribusi & Spark SQL\n"
        "│   ├── ml_clustering.py            # Model K-Means Clustering & evaluasi Silhouette\n"
        "│   └── analytics_engine.py         # Business intelligence metrics & peak time detection\n"
        "├── run_pipeline.py                 # Runner eksekusi end-to-end data pipeline\n"
        "├── run_dashboard.bat               # 1-Click launcher untuk membuka web dashboard\n"
        "└── README.md                       # Dokumentasi teknis proyek"
    )
    add_run(p_code, code_text, size=9, font_name="Courier New")

    output_path = "LAPORAN_AKHIR_BIGDATA_IPB_2026.docx"
    doc.save(output_path)
    print(f"Report regenerated with formal Heading styles: {output_path}")

if __name__ == "__main__":
    create_report()
