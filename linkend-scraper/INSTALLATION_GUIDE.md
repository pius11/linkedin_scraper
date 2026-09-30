# 🛠️ Installation & Setup Guide

This guide provides step-by-step instructions to set up the **LinkedIn Company About Scraper** environment on your local machine using Python and Playwright.

---

## 📋 System Prerequisites

Ensure you have the following prerequisites installed on your system:
- **Operating System:** Windows 10/11, macOS, or Linux.
- **Python:** Python `3.10` or higher.
  - To check your Python version, run:
    ```bash
    python --version
    ```
- **Git** (optional, for cloning the repository).

---

## 🚀 Step-by-Step Installation

### Step 1: Open Terminal & Navigate to Project Directory

Open PowerShell, Command Prompt, or your terminal and navigate to the project directory:

```bash
# Navigate to the project root folder
cd linkend-scraper
```

*(Replace `linkend-scraper` with the relative or absolute path where you cloned/saved the repository).*

---

### Step 2: Create a Virtual Environment (`venv`)

Creating an isolated virtual environment ensures that dependencies do not conflict with other Python projects on your machine.

**On Windows (PowerShell):**
```powershell
python -m venv venv
```

**Activate the Virtual Environment:**
```powershell
.\venv\Scripts\Activate.ps1
```

> **Note for Windows Users:**
> If you encounter an execution policy error like `cannot be loaded because running scripts is disabled on this system`, run:
> ```powershell
> Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
> .\venv\Scripts\Activate.ps1
> ```

---

### Step 3: Upgrade `pip` & Install Python Dependencies

With your virtual environment activated, install the required packages using the provided `requirements.txt` file:

```powershell
python -m pip install --upgrade pip
pip install -r requirements.txt
```

#### Core Dependencies Included:
- **`playwright`**: Headless/Headful Chromium automation engine.
- **`beautifulsoup4`**: Fast HTML DOM parsing and data extraction.
- **`pandas`**: Structured tabular data formatting and manipulation.
- **`openpyxl`**: Excel (`.xlsx`) export engine.
- **`pycountry`**: Standard ISO 3166 country and subdivision database.

---

### Step 4: Install Playwright Chromium Browser Binaries

Playwright requires its dedicated Chromium browser binaries to automate LinkedIn pages:

```powershell
playwright install chromium
```

*(This downloads the standalone, sandboxed Chromium engine used by Playwright).*

---

## ✅ Verification

To verify that your installation was successful, run a quick version check:

```powershell
python -c "import playwright, bs4, pandas, openpyxl, pycountry; print('All dependencies installed successfully!')"
```

If you see `All dependencies installed successfully!`, your environment is ready to use.

---

## 🔧 Troubleshooting Common Installation Issues

### 1. `playwright: command not found`
Make sure your virtual environment is active (`(venv)` shown in terminal) or use:
```powershell
python -m playwright install chromium
```

### 2. Missing C++ Redistributable on Windows
If Chromium fails to launch, ensure you have the [Visual C++ Redistributable](https://aka.ms/vs/17/release/vc_redist.x64.exe) installed.

---

👉 **Next Step:** Read the [Usage Guide](USAGE_GUIDE.md) to start scraping.
