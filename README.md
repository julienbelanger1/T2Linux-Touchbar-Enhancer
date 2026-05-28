# Touch Bar Enhancer 🎛️✨

![License](https://img.shields.io/badge/license-MIT-blue.svg)
![Python](https://img.shields.io/badge/python-3.10%2B-blue)
![PyQt6](https://img.shields.io/badge/PyQt6-Framework-green)

**Touch Bar Enhancer** is a simple Touch Bar configurator for Linux, designed specifically for Apple MacBook Pro laptops equipped with a Touch Bar running Linux (T2 Macs). 

It provides an intuitive graphical interface to configure layouts, map functions, and deploy settings directly to [`tiny-dfr`](https://github.com/ubports/tiny-dfr), the underlying daemon responsible for rendering the Touch Bar on Linux.

---

## 🚀 Features

- **Visual Layout Editor**: Easily add, arrange, and remove Touch Bar buttons visually.
- **Dual Layers Support**: Configure separate layouts for standard Function Keys (F1-F12) and Media Keys.
- **CupertinoIcons Integration**: Natively maps Apple's Cupertino icons to rasterized PNGs automatically, ensuring a native macOS look and feel.
- **Hardware Toggles**: Control critical Touch Bar features such as:
  - **Show Button Outlines**: Toggle visual borders around touch targets.
  - **Enable Pixel Shift**: Hardware burn-in protection for the OLED display.
  - **Adaptive Brightness**: Use the ambient light sensor to adjust Touch Bar brightness.
- **One-Click Deployment**: Generates `config.toml`, handles required PNG icon rendering, and automatically restarts the `tiny-dfr` daemon via `pkexec` (PolicyKit).

---

## 🛠️ Technology Stack

Touch Bar Enhancer is built using Python and frameworks:

- **Python (>= 3.10)**: Core programming language.
- **[PyQt6](https://www.riverbankcomputing.com/software/pyqt/)**: The foundation of the graphical user interface, utilizing the modern Fusion style and Wayland support.
- **[uv](https://github.com/astral-sh/uv)**: Used for extremely fast dependency management and environment isolation.
- **[tiny-dfr](https://github.com/ubports/tiny-dfr)**: The system-level Rust daemon that interfaces with the Touch Bar hardware. This application acts as a high-level frontend for it.
- **CupertinoIcons**: Embedded TrueType font utilized dynamically to render high-quality PNG icons for `tiny-dfr` on the fly.

---

## 📦 Installation & Usage

### Prerequisites

1. You must have a compatible MacBook Pro running Linux (T2 Mac).
2. Ensure [`tiny-dfr`](https://github.com/ubports/tiny-dfr) is installed and enabled on your system (`systemctl status tiny-dfr`).
3. Ensure `pkexec` (PolicyKit) is installed, as it is required to deploy configurations to system directories (`/etc/` and `/var/lib/`).

### Setup

Clone the repository and run the application using `uv`:

```bash
# Clone the repository
git clone https://github.com/julien/touchbarv2.git
cd touchbarv2

# Run the app directly using uv (it will handle dependencies)
uv run python -m touchbar_enhancer
```

### How to Use

1. **Select Layer**: Choose between editing the `F1-F12` layer or the `Media Keys` layer using the top toggle.
2. **Add Buttons**: Click items in the **Toolbox** (right pane) to add them to your active layout.
3. **Remove Buttons**: Click any button on the **Active Layout** preview (left pane) to remove it.
4. **Adjust Settings**: Toggle Pixel Shift, Adaptive Brightness, and Outlines.
5. **Deploy**: Click **Deploy to Touchbar**. You will be prompted for your user password via `pkexec` to apply the system-wide systemd and tiny-dfr configurations.

---

## ⚠️ Current Status: What Works vs. What Doesn't

### ✅ What Works
- **Graphical GUI & Previews**: The PyQt6 UI successfully renders your layout exactly as it will appear.
- **Icon Generation**: Translating vector CupertinoIcons fonts into static PNGs for `tiny-dfr` works flawlessly.
- **Daemon Management**: Safely injecting a `systemd` drop-in configuration and restarting the `tiny-dfr` service without manual terminal intervention.
- **Settings Persistence**: User configurations are successfully backed up to `~/.config/touchbar-enhancer/config.toml` and `/var/lib/touchbar-enhancer/`.

### ❌ What Doesn't (Known Limitations)
- **Drag-and-Drop Reordering**: Currently, you cannot drag items to rearrange them in the active layout. You must remove and re-add them in the correct order.
- **Custom SVGs**: Importing arbitrary `.svg` or `.png` files from the filesystem is not fully wired up yet; you are limited to the embedded `PRESETS` and Cupertino icons.
- **Non-systemd Init Systems**: The deploy script relies entirely on `systemd` drop-ins. Systems using OpenRC, runit, or dinit will need to apply the generated `/etc/tiny-dfr/config.toml` manually.
- **Wayland `pkexec` GUI Prompt**: Depending on your Wayland compositor, `pkexec` might fallback to the terminal or fail if a graphical authentication agent (like `polkit-kde-agent` or `polkit-gnome`) isn't running.

---

## 🔮 Potential Improvements & Roadmap

If you wish to contribute, the following features would be excellent additions:

1. **Drag-and-Drop Architecture**: Refactor the `QBoxLayout` preview to a list widget or custom canvas that supports Qt Drag & Drop events.
2. **Custom Icon Importer**: A file picker dialog allowing users to upload their own `.png` or `.svg` icons, copy them to `/var/lib/touchbar-enhancer/icons`, and append them to the toolbox.
3. **Multi-Profile Support**: Allow users to save and load different "Layout Profiles" (e.g., "Developer", "Media Editing", "Minimalist") to disk.
4. **Standalone AppImage / Flatpak**: Package the application so users don't need Python or `uv` installed, easing distribution across Fedora, Arch, and Ubuntu.
5. **Polkit Integration Alternative**: Replace `pkexec` shell scripts with a native DBus interface or `sudo` fallback to improve compatibility across different desktop environments.

---

## 📝 License

This project is open-source. MIT License.
