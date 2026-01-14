# 📖 Cho-Archive: Automated PDF Study Guide Generator

This tool automates the creation of professional study guides by converting a centralized Google Sheets database into structured, print-ready PDF formats.

## ✨ Key Features
- **Dual-Mode Output**:
  - **Concept + Problem Mode**: A dual-column layout for comprehensive learning.
  - **Concept-Only Mode**: A single-column summary layout for intensive review.
- **Smart PDF Layout Engine**: 
  - Automated layout-switching logic using CSS Media Queries and `page-break` controls.
  - Advanced regex pre-processing for architectural tables and bullet-point indentation.
- **Customized Generation**:
  - Filter and extract specific sections based on exam frequency or subject.
  - Automatic embedding of diagrams and visuals from Google Drive.
- **Print Optimization**: High-fidelity typography using Noto Sans KR, optimized for A4 paper.

## 🛠 Tech Stack
- **Language**: Python (Streamlit)
- **Styling**: Print-optimized CSS / HTML Injection
- **Data Management**: Pandas & Google Sheets CSV Export
