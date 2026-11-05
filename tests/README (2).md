{
  "projects": [
    {
      "id": "excel_cleaner",
      "name": "Excel Cleaner",
      "description": "Clean and normalize Excel / CSV files.",
      "status": "Active",
      "ui": {
        "widgets": [
          {
            "type": "label",
            "text": "Input"
          },
          {
            "type": "button",
            "text": "Select source file",
            "action": "choose_file"
          },
          {
            "type": "separator"
          },
          {
            "type": "entry",
            "label": "Output name",
            "placeholder": "cleaned_output.xlsx"
          },
          {
            "type": "switch",
            "label": "Create backup"
          },
          {
            "type": "button",
            "text": "Run cleaner",
            "action": "run_demo",
            "params": {
              "project": "Excel Cleaner"
            }
          },
          {
            "type": "button",
            "text": "Open output folder",
            "action": "open_output"
          }
        ]
      }
    },
    {
      "id": "bank_reconcile",
      "name": "Bank Reconciliation",
      "description": "Match transactions and generate a reconciliation report.",
      "status": "Draft",
      "ui": {
        "widgets": [
          {
            "type": "button",
            "text": "Select bank statement",
            "action": "choose_file"
          },
          {
            "type": "button",
            "text": "Select ERP export",
            "action": "choose_file"
          },
          {
            "type": "switch",
            "label": "Strict matching"
          },
          {
            "type": "button",
            "text": "Run reconciliation",
            "action": "run_demo",
            "params": {
              "project": "Bank Reconciliation"
            }
          }
        ]
      }
    },
    {
      "id": "roberto",
      "name": "Roberto",
      "description": "Invoice collection, PDF parsing and matching pipeline.",
      "status": "Active",
      "ui": {
        "widgets": [
          {
            "type": "button",
            "text": "Select PPR file",
            "action": "choose_file"
          },
          {
            "type": "switch",
            "label": "Enable OCR fallback"
          },
          {
            "type": "button",
            "text": "Run pipeline",
            "action": "run_demo",
            "params": {
              "project": "Roberto"
            }
          },
          {
            "type": "button",
            "text": "View results",
            "action": "open_output"
          }
        ]
      }
    }
  ]
}