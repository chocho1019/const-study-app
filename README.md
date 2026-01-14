# 🏛️ Cho-Archive: Architecture License Exam Prep App

A high-performance web application designed for students preparing for the **Korea National Architectural Engineer License**. This app bridges the gap between raw study data and strategic learning.

## ✨ Key Features
- **Smart Learning Management**:
  - **Contextual Mapping**: Bridges theoretical concepts with actual past exam questions for instant feedback.
  - **Efficiency Filters**: High-frequency filter (3+ appearances) and frequency-based sorting to maximize study ROI.
  - **Hierarchical Categorization**: Structured browsing by Subject, Main Category, and Sub Category.
- **Dynamic Learning Modes**:
  - **All-in-one List**: Full textbook view.
  - **Flashcard Mode**: Randomized study for deep memorization.
- **Real-time Sync & Auth**:
  - **Persistent Favorites**: "Heart" system synced directly to Google Sheets via `gspread`.
  - **Secure Login**: Email-based authentication integrated with GCP.

## 🛠 Tech Stack
- **Frontend/Backend**: Streamlit
- **Database**: Google Sheets (via Gspread API)
- **Data Engine**: Pandas (Dynamic Filtering & Sorting)
