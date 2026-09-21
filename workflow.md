{
  "name": "My workflow",
  "nodes": [
    {
      "parameters": {
        "updates": [
          "message"
        ],
        "additionalFields": {
          "download": false
        }
      },
      "id": "b8c06610-9a72-46e0-a98d-df1fb4b74b71",
      "name": "Telegram Trigger",
      "type": "n8n-nodes-base.telegramTrigger",
      "typeVersion": 1.5,
      "position": [
        -144,
        -48
      ],
      "webhookId": "802eabe1-3300-4900-bb8f-0648a47ab470",
      "credentials": {
        "telegramApi": {
          "id": "spFJ9x29v5rOGfNt",
          "name": "Telegram account"
        }
      }
    },
    {
      "parameters": {
        "promptType": "define",
        "text": "={{ $json.message.text }}",
        "options": {
          "systemMessage": "You are an expert AI Dispensing Defect Detective assisting manufacturing operators on Telegram.\n\nYOUR PRIMARY GOAL:\nGuide the user through a structured troubleshooting process for fluid dispensing defects (e.g., solder paste, epoxy, underfill, adhesives) by evaluating key process parameters.\n\nPROCESS PARAMETERS TO CONSIDER:\n- Dispensing Volume / Diameter\n- Dispensing Pressure\n- Dispensing Speed / Flow Rate\n- Dispensing Time\n- Dispensing Height\n- Nozzle Size / Condition\n- Material Properties (Viscosity, Temperature, Curing Characteristics)\n\nDIAGNOSTIC PROCESS & MEMORY:\n1. Check conversation memory to see what parameters or details the user has already provided.\n2. Collect answers to these 5 core diagnostic questions (ask 1 or 2 at a time, NEVER all at once):\n   - What material is being dispensed? (Determines baseline viscosity and properties)\n   - Is the dispensing amount/diameter too large or too small compared to thresholds?\n   - Is the defect happening continuously or occasionally?\n   - Have any parameters recently changed? (e.g., nozzle size, dispensing height, pressure, speed, time, or material batch)\n   - Is the defect happening at one location or across multiple locations?\n\nREFERENCE THRESHOLDS (DATA TABLE TOOL):\n- You have a tool named \"Get row(s) in Data table\" that reads the \"reference\" table of standard dispensing thresholds.\n- Each row contains standard specification fields in millimeters (target_diameter_mm, min_diameter_mm, max_diameter_mm).\n- Whenever the user provides a measured diameter, ALWAYS call \"Get row(s) in Data table\" first to fetch current limits. Do NOT hardcode or guess numbers.\n- Compare measured values against fetched thresholds:\n   - measured < min_diameter_mm: Undersized / Insufficient Material.\n   - measured > max_diameter_mm: Oversized / Excessive Spreading.\n   - min <= measured <= max: Acceptable / Pass.\n- Always cite the exact threshold numbers fetched (e.g., \"Your measured 0.35 mm is below the 0.40 mm minimum limit\").\n\nCAUSE ANALYSIS LOGIC:\nUse parameter relationships when evaluating causes:\n- Continuous Undersized: Likely nozzle partial blockage, pressure drop, dispensing height too high, or increased material viscosity.\n- Continuous Oversized: Likely excessive pressure, long dispensing time, low viscosity, or nozzle size too large.\n- Occasional / Random Variations: Likely air bubbles trapped in syringe barrel, speed/flow rate instability, or temperature-driven viscosity drift.\n\nOUTPUT STYLE & FORMAT:\n- Speak naturally like a helpful engineering teammate on Telegram.\n- DO NOT use rigid headers or Q&A templates.\n- Keep messages short (2–4 sentences max) to maintain a natural chat flow.\n- Once all 5 diagnostic details are gathered, output:\n  1) Detected Defect & Confidence Score (%)\n  2) Probable Root Cause (explain WHY based on parameters like pressure, viscosity, nozzle size, height, or speed)\n  3) Recommended 3-step action plan\n  4) Ask: \"Did this fix the issue?\""
        }
      },
      "id": "25237334-2924-4480-b01f-ef96ade91a0f",
      "name": "AI Agent",
      "type": "@n8n/n8n-nodes-langchain.agent",
      "typeVersion": 3.1,
      "position": [
        144,
        -48
      ],
      "alwaysOutputData": true,
      "retryOnFail": true,
      "maxTries": 5,
      "waitBetweenTries": 2000
    },
    {
      "parameters": {
        "modelName": "models/gemini-3.5-flash-lite",
        "options": {}
      },
      "id": "8d43edb7-efbd-48e8-9c33-4e3411a62e2b",
      "name": "Google Gemini Chat Model",
      "type": "@n8n/n8n-nodes-langchain.lmChatGoogleGemini",
      "typeVersion": 1.1,
      "position": [
        96,
        192
      ],
      "credentials": {
        "googlePalmApi": {
          "id": "osXqe6LFgJf8iJue",
          "name": "Google Gemini(PaLM) Api account"
        }
      }
    },
    {
      "parameters": {
        "sessionIdType": "customKey",
        "sessionKey": "={{ $('Telegram Trigger').item.json.message.chat.id }}",
        "contextWindowLength": 10
      },
      "id": "cb4c361b-8112-4250-ad20-e681fca63f20",
      "name": "Simple Memory",
      "type": "@n8n/n8n-nodes-langchain.memoryBufferWindow",
      "typeVersion": 1.4,
      "position": [
        224,
        192
      ]
    },
    {
      "parameters": {
        "operation": "get",
        "dataTableId": {
          "__rl": true,
          "value": "NmHwCZmmo84I6F7y",
          "mode": "list",
          "cachedResultName": "reference",
          "cachedResultUrl": "/projects/0ZxlppqSPseBURCQ/datatables/NmHwCZmmo84I6F7y"
        }
      },
      "id": "d729e60c-aedc-4885-943f-687567f656f1",
      "name": "Get row(s) in Data table",
      "type": "n8n-nodes-base.dataTableTool",
      "typeVersion": 1.1,
      "position": [
        352,
        192
      ]
    },
    {
      "parameters": {
        "chatId": "={{ $('Telegram Trigger').item.json.message.chat.id }}",
        "text": "={{ $json.output }}",
        "additionalFields": {
          "parse_mode": "Markdown"
        }
      },
      "id": "ad8e9ca3-0a36-4054-aa81-11b35d5404b0",
      "name": "Send a text message1",
      "type": "n8n-nodes-base.telegram",
      "typeVersion": 1.2,
      "position": [
        544,
        -48
      ],
      "webhookId": "3d87ed04-f075-4a6e-81db-a427a3626836",
      "credentials": {
        "telegramApi": {
          "id": "spFJ9x29v5rOGfNt",
          "name": "Telegram account"
        }
      }
    }
  ],
  "pinData": {},
  "connections": {
    "Telegram Trigger": {
      "main": [
        [
          {
            "node": "AI Agent",
            "type": "main",
            "index": 0
          }
        ]
      ]
    },
    "AI Agent": {
      "main": [
        [
          {
            "node": "Send a text message1",
            "type": "main",
            "index": 0
          }
        ]
      ]
    },
    "Google Gemini Chat Model": {
      "ai_languageModel": [
        [
          {
            "node": "AI Agent",
            "type": "ai_languageModel",
            "index": 0
          }
        ]
      ]
    },
    "Simple Memory": {
      "ai_memory": [
        [
          {
            "node": "AI Agent",
            "type": "ai_memory",
            "index": 0
          }
        ]
      ]
    },
    "Get row(s) in Data table": {
      "ai_tool": [
        [
          {
            "node": "AI Agent",
            "type": "ai_tool",
            "index": 0
          }
        ]
      ]
    }
  },
  "active": true,
  "settings": {
    "executionOrder": "v1",
    "binaryMode": "separate"
  },
  "versionId": "45607005-059e-44da-8a9e-e603140e6ddf",
  "meta": {
    "templateCredsSetupCompleted": true,
    "instanceId": "4a9f6d1c998d2ea0a0436ede594367aadc215abe63415ea17c5d18107984387e"
  },
  "nodeGroups": [],
  "id": "x6sgzCS2SetPCo8q",
  "tags": []
}