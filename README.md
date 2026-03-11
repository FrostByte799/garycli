<div align="center">

# 🗡️ GARY CLI: The Spear Carrier

**Piercing the Silicon with AI.** <br>
*An AI-native command-line development and debugging agent purpose-built for STM32*

[![License](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)
[![Python](https://img.shields.io/badge/Python-3.8+-green.svg)](https://www.python.org/)
[![STM32](https://img.shields.io/badge/STM32-F0%20F1%20F3%20F4-blue.svg)](#supported-chips)
[![Website](https://img.shields.io/badge/Website-garycli.com-success)](https://www.garycli.com)

<br>

```
   ██████╗  █████╗ ██████╗ ██╗   ██╗
  ██╔════╝ ██╔══██╗██╔══██╗╚██╗ ██╔╝
  ██║  ███╗███████║██████╔╝ ╚████╔╝
  ██║   ██║██╔══██║██╔══██╗  ╚██╔╝
  ╚██████╔╝██║  ██║██║  ██║   ██║
   ╚═════╝ ╚═╝  ╚═╝╚═╝  ╚═╝   ╚═╝
```

**Talk in natural language and let AI directly control your STM32 hardware.**

<p align="center">
  <a href="./README_CN.md"><b>简体中文</b></a> | <a href="./README.md"><b>English</b></a>
</p>

[Quick Start](#-quick-start) · [Features](#-core-features) · [User Guide](#-user-guide) · [Command Reference](#-command-reference) · [Skill System](#-skill-system-skills) · [FAQ](#-faq)
</div>

---

## ⚡ What is Gary?

In traditional embedded development, engineers spend 80% of their effort reading hundreds of pages of Reference Manuals, configuring registers, and dealing with mysterious wiring issues.

**Gary (The Spear Carrier)** is not just another code generator — it is an AI agent that can **directly intervene in your physical hardware**. You only need to describe your requirements in natural language, and Gary will automatically complete the **full closed loop** from code generation, cross-compilation, and physical flashing to error self-healing.

```
You say: "Help me make a program that displays temperature and humidity on an OLED, using an AHT20 sensor"

Gary automatically executes:
  ✓ Generate a complete main.c (HAL library + I2C driver + OLED display)
  ✓ Cross-compile with arm-none-eabi-gcc
  ✓ Flash to STM32 via UART/SWD
  ✓ Monitor serial output and verify startup
  ✓ Read registers to confirm peripheral status
  ✗ Detect no I2C response → automatically analyze the cause → fix the code → reflash
  ✓ Succeeds on round 2, program runs normally
```

---

## 🎯 Core Features

### 🗣️ Natural Language → Hardware Control

No more digging through Reference Manuals. Just say what you want in plain language, and Gary generates complete, compilable STM32 HAL C code.

```bash
gary do "PA0 is connected to an LED, help me make a breathing light with a PWM frequency of 1kHz"
gary do "Use I2C1 to read MPU6050 acceleration data and print it over serial"
gary do "Configure TIM2 encoder mode to read motor speed"
```

### 🔄 Fully Automated Closed-Loop Debugging

Gary’s core capability is not "generating code" — it is **automatically verifying and fixing it**:

```
Compile → Flash → Read serial → Read registers → Analyze results
  ↑                                      ↓
  └──── Automatically fix code ←── Find problem ←──────┘
```

* **Compilation failed** → Read GCC error messages and automatically fix the code
* **HardFault** → Analyze SCB_CFSR/HFSR registers and locate the exact cause
* **Program hangs** → Check SysTick, I2C bus lockup, and clock configuration
* **Sensor not responding** → Detect I2C NACK/ARLO and determine whether the issue is unconnected hardware or a wrong address
* **Up to 8 rounds of automatic repair**; if it still cannot be fixed, Gary will tell you the exact hardware problem

### ⚡ Flashing

Gary **prefers SWD flashing by default**, and when a scenario requires register-level debugging, it automatically switches to SWD plus serial communication.

### 🧰 Built-in Toolset

| Tool                            | Purpose                                                                                                            |
| ------------------------------- | ------------------------------------------------------------------------------------------------------------------ |
| **PID Auto-Tuning**             | Analyze response curves (overshoot / oscillation / steady-state error) and automatically recommend Kp/Ki/Kd        |
| **I2C Bus Scan**                | Scan all device addresses and automatically identify 100+ common chip models                                       |
| **Pin Conflict Detection**      | Staticaly analyze code to detect duplicate pin configuration, accidental SWD occupation, and similar issues        |
| **PWM Frequency Scan**          | Automatically calculate PSC/ARR and generate frequency scan tables for motors/buzzers                              |
| **Servo Calibration**           | Generate angle sweep code to precisely map pulse width to angle                                                    |
| **Signal Acquisition Analysis** | Analyze ADC/sensor data noise, signal-to-noise ratio, and frequency characteristics                                |
| **Peripheral Smoke Test**       | One-click generation of minimal test code for GPIO/UART/I2C/SPI/ADC                                                |
| **Flash/RAM Analysis**          | Display firmware resource usage and warn about Flash overflow                                                      |
| **Power Estimation**            | Estimate MCU current draw and power consumption based on enabled peripherals                                       |
| **Font Bitmap Generation**      | Convert arbitrary Chinese/English text into OLED dot-matrix C arrays (rendered with system fonts, not handwritten) |

### 🔌 Bring Your Own Key

Gary is not tied to any AI provider. Your API key, your choice:

| Provider        | Model             | Notes                        |
| --------------- | ----------------- | ---------------------------- |
| DeepSeek        | deepseek-chat     | Best value for money         |
| Kimi / Moonshot | kimi-k2.5         | Strong Chinese capability    |
| OpenAI          | gpt-4o            | Strong overall capability    |
| Google Gemini   | gemini-2.0-flash  | Large free quota             |
| Tongyi Qianwen  | qwen-plus         | Alibaba Cloud                |
| Zhipu GLM       | glm-4-flash       | Free                         |
| Ollama          | qwen2.5-coder:14b | Local offline, fully private |

### 🧩 Skill System (Skills)

Extend Gary’s capabilities through **pluggable skill packages**:

```bash
/skill install pid_tuner.py              # Install from a .py file
/skill install ~/Downloads/skill.zip     # Install from a compressed package
/skill install https://github.com/xxx    # Install from a Git repository
/skill list                               # View all skills
/skill create my_tool "My Tool"          # Create a new skill template
/skill export my_tool                     # Package and share it with others
```

Each Skill contains tool functions + AI schema + prompt files, and **takes effect immediately after installation** with no restart required.

---

## 🚀 Quick Start

### One-Click Installation

**Linux / macOS / WSL:**

```bash
curl -fsSL https://www.garycli.com/install.sh | bash
```

**Windows (PowerShell as Administrator):**

```powershell
irm https://www.garycli.com/install.ps1 | iex
```

The installation script will automatically complete:

* Python environment detection
* arm-none-eabi-gcc cross-compiler installation
* STM32 HAL library download
* Python dependency installation (openai, rich, pyserial, pyocd, etc.)
* Serial flashing tool installation (stm32loader)

### Manual Installation

```bash
# 1. Clone the repository
git clone https://github.com/PrettyMyGirlZyy4Embedded/garycli.git
cd garycli

# 2. Install Python dependencies
pip install -r requirements.txt

# 3. Install the cross-compiler
# Ubuntu/Debian:
sudo apt install gcc-arm-none-eabi
# macOS:
brew install --cask gcc-arm-embedded
# Windows: Download and install from the ARM official website

# 4. Install the serial flashing tool (optional, recommended)
pip install stm32loader

# 5. Install debugger drivers (optional)
pip install pyocd

# 6. Download the HAL library
python3 setup.py --hal

# 7. Run environment diagnostics
python3 stm32_agent.py --doctor
```

### Initial Configuration

```bash
# Configure the AI backend (interactive wizard)
gary config
```

Follow the prompts to choose a provider and enter your API key. DeepSeek (cheap and effective) or Ollama (fully local) is recommended.

### Environment Diagnostics

```bash
gary doctor
```

Example output:

```
■ AI Interface
  ✓ API Key   sk-abc...xyz
  ✓ Base URL  https://api.deepseek.com/v1
  ✓ Model     deepseek-chat
  ✓ API Connectivity  Test passed

■ Compilation Toolchain
  ✓ arm-none-eabi-gcc  arm-none-eabi-gcc (15.1.0) 15.1.0
  ✓ HAL Libraries      STM32F0xx, STM32F1xx, STM32F3xx, STM32F4xx
  ✓ CMSIS Core

■ Python Dependencies
  ✓ openai
  ✓ rich
  ✓ prompt_toolkit
  ✓ pyserial  (optional)
  ✓ pyocd  (optional)
  ✓ stm32loader  (optional)

■ Hardware Probes
  ✓ STM32 STLink V2  (066BFF...)
  ✓ Serial Port /dev/ttyUSB0

  ✅  All core configuration is normal. Gary is ready!
```

---

## 📖 User Guide

### Mode 1: Single Task (`gary do`)

Run one command and exit without launching the interactive interface:

```bash
# Generate + compile (no hardware)
gary do "Write a WS2812 LED strip driver to control 8 LEDs with a rainbow animation"

# Generate + compile + flash (hardware connected)
gary do "PA0 LED blinking, 500ms interval" --connect

# Specify the chip model
gary do "Read ADC voltage and print over serial" --chip STM32F407VET6 --connect
```

### Mode 2: Interactive Conversation (`gary`)

Launch the immersive TUI for continuous conversational and iterative development:

```bash
gary                        # Start
gary --connect              # Start and automatically connect hardware
gary --chip STM32F407VET6   # Specify chip model
```

After entering:

```
Gary > Help me make an OLED clock, connect SSD1306 to I2C1, and display hours, minutes, and seconds

  🔧 stm32_reset_debug_attempts → Counter reset
  🔧 stm32_hardware_status → chip: STM32F103C8T6, hw_connected: true
  🔧 stm32_generate_font → Generated bitmap for "0123456789:"
  🔧 stm32_auto_flash_cycle → Compilation successful, 8.2KB, flashing successful...
  Serial output: Gary:BOOT → OLED Init OK → 12:34:56

✓ Compilation and flashing successful, 8.2KB. OLED is now displaying the time.

Gary > Add a button to adjust the time. Connect the button to PA1. Short press switches hours/minutes/seconds, long press adds 1.

  🔧 str_replace_edit → Replaced button-related code
  🔧 stm32_auto_flash_cycle → Compilation successful, 9.1KB, flashing successful...

✓ Button-based time adjustment has been added. Short press switches the field, long press adds 1.
```

### Mode 3: Incremental Modifications

Gary remembers your previous code. You can keep iterating continuously:

```
Gary > The LED blinks too fast, change it to 1 second
Gary > Change it to a common-anode seven-segment display
Gary > Add a buzzer that sounds during alarms
Gary > Change the I2C address from 0x3C to 0x3D
```

Gary only modifies the parts you request and does not rewrite the whole program.

---

## 📋 Command Reference

### Terminal Commands

| Command                      | Description                                       |
| ---------------------------- | ------------------------------------------------- |
| `gary`                       | Launch the interactive conversation interface     |
| `gary do "task description"` | Single-task mode                                  |
| `gary do "task" --connect`   | Single-task mode + automatically connect hardware |
| `gary --chip STM32F407VET6`  | Specify the chip model                            |
| `gary --connect`             | Start and connect hardware                        |
| `gary config`                | Configure AI backend (API key / model)            |
| `gary doctor`                | Environment diagnostics (check all configuration) |

### Interactive Commands (entered at the `Gary >` prompt)

| Command                     | Description                                                     |
| --------------------------- | --------------------------------------------------------------- |
| `/connect [chip]`           | Connect SWD debugger (for example `/connect STM32F103C8T6`)     |
| `/disconnect`               | Disconnect hardware                                             |
| `/serial [port] [baudrate]` | Connect serial port (for example `/serial /dev/ttyUSB0 115200`) |
| `/serial list`              | List available serial ports                                     |
| `/chip [model]`             | View/switch chip model                                          |
| `/flash [uart\|swd\|auto]`  | Switch flashing mode                                            |
| `/flash status`             | View flashing tool status                                       |
| `/probes`                   | List all debug probes                                           |
| `/status`                   | View full hardware status                                       |
| `/config`                   | Configure AI interface                                          |
| `/projects`                 | List historical projects                                        |
| `/skill list`               | List installed skills                                           |
| `/skill install <source>`   | Install a skill package                                         |
| `/skill create <name>`      | Create a skill template                                         |
| `/clear`                    | Clear conversation history                                      |
| `/exit`                     | Exit                                                            |

---

## 🔧 Hardware Wiring

### Setup: Serial + SWD

Add one more debugger (ST-Link V2, ¥10) to read registers and analyze HardFaults:

```
ST-Link           STM32
  SWDIO ─────────── PA13
  SWCLK ─────────── PA14
  GND ──────────── GND
  3.3V ─────────── 3.3V

USB-TTL           STM32 (serial monitoring)
  TX  ──────────→ PA10
  RX  ←────────── PA9
  GND ──────────── GND
```

---

## 🧩 Skill System (Skills)

Gary extends functionality through pluggable **skill packages**. Each Skill is a standard directory:

```
~/.gary/skills/
├── pid_tuner/
│   ├── skill.json        ← Metadata (name, version, author, dependencies)
│   ├── tools.py          ← Tool functions (Python)
│   ├── schemas.json      ← AI invocation format (OpenAI Function Calling)
│   ├── prompt.md         ← Teach the AI when to use these tools
│   └── requirements.txt  ← Python dependencies
├── uart_flash/
└── _disabled/            ← Disabled skills
```

### Install Skills

```bash
# From a .py file (automatically wrapped into a skill)
/skill install stm32_extra_tools.py

# From a zip package
/skill install ~/Downloads/gary_skill_pid_tuner.zip

# From a Git repository
/skill install https://github.com/someone/gary-skill-motor.git

# From a local directory
/skill install ~/my_skills/sensor_kit/
```

### Manage Skills

```bash
/skill list                  # List all (including disabled)
/skill info pid_tuner        # View details
/skill disable pid_tuner     # Temporarily disable
/skill enable pid_tuner      # Re-enable
/skill uninstall pid_tuner   # Uninstall
/skill reload                # Hot reload all
```

### Develop Your Own Skill

```bash
# 1. Generate a template
/skill create motor_driver "DC Motor PID Control Tool"

# 2. Edit the generated files
#    ~/.gary/skills/motor_driver/tools.py     ← Write tool functions
#    ~/.gary/skills/motor_driver/schemas.json ← Write AI schema
#    ~/.gary/skills/motor_driver/prompt.md    ← Write usage guide

# 3. Hot reload
/skill reload

# 4. Package and share
/skill export motor_driver
# → gary_skill_motor_driver.zip
```

### Skill Development Specification

**tools.py** (must export `TOOLS_MAP`):

```python
def motor_set_speed(rpm: int) -> dict:
    """Set motor speed"""
    return {"success": True, "message": f"Target speed: {rpm} RPM"}

TOOLS_MAP = {
    "motor_set_speed": motor_set_speed,
}
```

**schemas.json** (OpenAI Function Calling format):

```json
[
  {
    "type": "function",
    "function": {
      "name": "motor_set_speed",
      "description": "Set target speed for a DC motor",
      "parameters": {
        "type": "object",
        "properties": {
          "rpm": {"type": "integer", "description": "Target speed in RPM"}
        },
        "required": ["rpm"]
      }
    }
  }
]
```

**prompt.md** (teach the AI how to use it):

```markdown
## Motor Control
When the user wants to control a motor, call motor_set_speed to set the target speed.
```

---

## 🏗️ Architecture

```
┌──────────────────────────────────────────────────────┐
│                    Gary CLI (TUI)                     │
│              rich + prompt_toolkit                    │
├──────────────────────────────────────────────────────┤
│                  AI Conversation Engine               │
│         OpenAI API (streaming + Function Calling)     │
│    DeepSeek │ Kimi │ GPT │ Gemini │ Ollama │ ...     │
├──────────────┬──────────────┬────────────────────────┤
│ Code Generation │ Compiler   │    Hardware Backend    │
│   STM32 HAL     │ GCC Cross  │  ┌─────────────────┐  │
│   C Templates   │ Compiler   │  │ UART ISP (preferred) │
│                 │            │  │  stm32loader     │  │
│                 │            │  ├─────────────────┤  │
│                 │            │  │ SWD (fallback)   │  │
│                 │            │  │  pyocd           │  │
│                 │            │  ├─────────────────┤  │
│                 │            │  │ Serial Monitor   │  │
│                 │            │  │  pyserial        │  │
│                 │            │  └─────────────────┘  │
├──────────────┴──────────────┴────────────────────────┤
│                  Skill System (Skills)                │
│ PID Tuning │ I2C Scan │ PWM Scan │ Font Gen │ Custom... │
└──────────────────────────────────────────────────────┘
         ↕ USB                    ↕ USB
┌──────────────┐          ┌──────────────────┐
│  USB-TTL     │          │  ST-Link/J-Link  │
│  (CH340)     │          │  (optional)      │
└──────┬───────┘          └──────┬───────────┘
       │ UART                    │ SWD
┌──────┴─────────────────────────┴───────────┐
│              STM32 Target Board            │
│   PA9/PA10 (UART)    PA13/PA14 (SWD)       │
└────────────────────────────────────────────┘
```

---

## <a name="supported-chips"></a> 📟 Supported Chips

| Series      | Typical Models                          | Flash       | RAM       |
| ----------- | --------------------------------------- | ----------- | --------- |
| **STM32F0** | F030F4, F030C8, F072CB                  | 16-128 KB   | 4-16 KB   |
| **STM32F1** | F103C8T6 (BluePill), F103RCT6, F103ZET6 | 64-512 KB   | 20-64 KB  |
| **STM32F3** | F303CCT6, F303RCT6                      | 256 KB      | 40 KB     |
| **STM32F4** | F401CCU6, F407VET6, F411CEU6            | 256-1024 KB | 64-128 KB |

> Other models: Gary will automatically download the corresponding CMSIS Pack (upon first connection). In theory, all Cortex-M series are supported.

---

## 💡 Practical Examples

### 🔰 Beginner: LED Blinking

```
Gary > Help me make an LED blink, PA0 pin, 500ms interval
```

### 🔢 Seven-Segment Display

```
Gary > 4-digit common-anode seven-segment display, PA0-PA7 for segment select, PB0-PB3 for digit select, display a counter
```

### 📡 Sensor Reading

```
Gary > Connect an AHT20 temperature and humidity sensor to I2C1 and print temperature and humidity over serial
Gary > Add an SSD1306 OLED to display the temperature too
```

### 🎛️ PID Motor Speed Control

```
Gary > DC motor PID speed control: TIM2 CH1 outputs PWM, TIM3 encoder reads feedback, target 500rpm
```

Gary will automatically: generate PID code → flash → collect serial data → analyze response → tune parameters → reflash → loop until stable.

### 🔍 I2C Device Troubleshooting

```
Gary > I connected several I2C devices but I'm not sure of their addresses, help me scan them
```

### 🎵 Buzzer Music

```
Gary > Passive buzzer connected to PA1, help me play a section of "Twinkle Twinkle Little Star"
```

### 🖥️ OLED Chinese Display

```
Gary > Display the Chinese text "你好世界" on the OLED, font size 16x16
```

Gary automatically calls the font bitmap generation tool to render true dot-matrix glyphs using system fonts, not handwritten data.

---

## 📁 Project Structure

```
gary/
├── stm32_agent.py          # Main program (TUI + AI conversation + tool framework)
├── compiler.py             # GCC cross-compiler wrapper
├── config.py               # Configuration file (API key, chip, paths)
├── setup.py                # Installation script
├── stm32_uart_flash.py     # UART ISP flashing module
├── stm32_extra_tools.py    # Extended toolset (PID/I2C/PWM/signal analysis...)
├── gary_skills.py          # Skill system manager
├── requirements.txt        # Python dependencies
└── ~/.gary/                # User data directory
    ├── skills/             # Installed skills
    ├── projects/           # Historical project archives
    └── skills_registry.json
```

---

## ❓ FAQ

### Installation

<details>
<summary><b>Q: arm-none-eabi-gcc cannot be found after installation?</b></summary>

Make sure it has been added to PATH:

```bash
which arm-none-eabi-gcc
# If there is no output, add it manually:
export PATH=$PATH:/usr/lib/arm-none-eabi/bin
```

Or run `gary doctor` to view diagnostic results.

</details>

<details>
<summary><b>Q: HAL library download failed?</b></summary>

```bash
# Download manually
python3 setup.py --hal

# Or specify series
python3 setup.py --hal f1 f4
```

</details>

<details>
<summary><b>Q: Serial port permission issue on Windows?</b></summary>

Make sure the CH340/CP2102 driver is installed. Confirm in Device Manager that the COM port has been recognized.

</details>

<details>
<summary><b>Q: Cannot open serial port on Linux (Permission denied)?</b></summary>

```bash
sudo usermod -aG dialout $USER
newgrp dialout
```

</details>

### Usage

<details>
<summary><b>Q: No response during serial flashing?</b></summary>

Checklist:

1. Is the BOOT0 jumper set to 1 (VCC side)?
2. Did you press the reset button?
3. Are TX/RX cross-connected? (TTL-TX → STM32-PA10)
4. Is the serial baud rate set to 115200?

</details>

<details>
<summary><b>Q: Compilation error `undefined reference to _sbrk`?</b></summary>

The code uses `sprintf` / `printf` / `malloc`. Gary-generated code does not use these functions. If you added them manually, replace them with Gary’s `Debug_Print` / `Debug_PrintInt`.

</details>

<details>
<summary><b>Q: How do I troubleshoot a HardFault?</b></summary>

After Gary connects through SWD, it automatically reads the SCB_CFSR register for analysis. Common causes:

* `PRECISERR`: Accessed a peripheral whose clock was not enabled
* `UNDEFINSTR`: Stack overflow or invalid function pointer
* `IACCVIOL`: Illegal Flash address

</details>

<details>
<summary><b>Q: Can I use a local Ollama model?</b></summary>

Yes. Run `gary config`, choose Ollama, and it is recommended to use `qwen2.5-coder:14b` or a larger model. Smaller models (7B) have weaker function-calling capability.

</details>

<details>
<summary><b>Q: Does it support Arduino / ESP32?</b></summary>

Currently only STM32 is supported. ESP32/Arduino support is on the roadmap.

</details>

---

## 🗺️ Roadmap

* [x] Full STM32F1/F4 series support
* [x] UART serial flashing (no debugger required)
* [x] PID auto-tuning
* [x] Skill system (Skills)
* [ ] Skill marketplace (browse/install community skills online)
* [ ] Visualized waveforms (real-time plotting of serial data)
* [ ] ESP32 support
* [ ] STM32CubeMX project import
* [ ] VS Code extension

---

## 🤝 Contributing

Issues and PRs are welcome! Contributions in the following areas are especially appreciated:

* **New Skill packages**: Package your tools as standard Skills and share them with the community
* **Chip support**: Adapt register address tables for more STM32 series
* **Documentation translation**: Help translate into English / other languages
* **Bug fixes**: Any issue encountered during use

### Develop a Skill and Contribute It

```bash
# 1. Create a skill template
/skill create my_awesome_tool "My Tool"

# 2. Develop & test
# Edit the files under ~/.gary/skills/my_awesome_tool/

# 3. Export
/skill export my_awesome_tool

# 4. Submit a PR to the skills/ directory of this repository
```

---

## 📜 License

This project is open source under the [Apache-2.0 License](https://opensource.org/licenses/Apache-2.0).

---

<div align="center">

**🗡️ Just Gary Do It.**

[Official Website](https://www.garycli.com) · [GitHub](https://github.com/GaryCLI/gary) · [Report Issues](https://github.com/GaryCLI/gary/issues)

</div>
