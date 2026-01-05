#!/usr/bin/env python3

from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QFormLayout,
    QTabWidget, QLabel, QSpinBox, QPushButton, QComboBox, QRadioButton,
    QMessageBox
)
from razer_common import (
    scan_razer_devices,
    construct_razer_report,
    build_arguments,
    send_report_to_device,
    is_mouse_device,
    is_keyboard_device,
    MOUSE_TARGET_PID, BW3PRO_WIRED_PID, BW3PRO_WIRELESS_PID,
    MOUSE_EFFECT_STATIC, KBD_EFFECT_STATIC,
    MOUSE_EFFECT_BREATHING, KBD_EFFECT_BREATHING,
    MOUSE_EFFECT_WAVE, KBD_EFFECT_WAVE,
    MOUSE_EFFECT_REACTIVE, KBD_EFFECT_REACTIVE,
    MOUSE_TRANSACTION_ID, MOUSE_CMD_CLASS, MOUSE_CMD_ID, MOUSE_DATA_SIZE,
    KBD_WIRED_TRANSACTION_ID, KBD_WIRELESS_TRANSACTION_ID, KBD_CMD_CLASS, KBD_CMD_ID, KBD_DATA_SIZE,
    MOUSE_SCROLL_WHEEL_LED, KBD_BACKLIGHT_LED
)

class MainWindow(QMainWindow):
    def __init__(self, debug_mode=False):
        super().__init__()
        self.debug_mode = debug_mode
        self.setWindowTitle("Razer Control")
        self.setMinimumSize(500, 400)
        self.init_ui()
        self.refresh_devices()

    def init_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)

        top_layout = QHBoxLayout()
        self.device_combo = QComboBox()
        self.btn_refresh = QPushButton("Refresh")
        self.btn_refresh.clicked.connect(self.refresh_devices)
        top_layout.addWidget(QLabel("Select Device:"))
        top_layout.addWidget(self.device_combo)
        top_layout.addWidget(self.btn_refresh)
        layout.addLayout(top_layout)

        self.tabs = QTabWidget()
        layout.addWidget(self.tabs)

        self.tab_static = self.create_tab_static()
        self.tab_breathing = self.create_tab_breathing()
        self.tab_wave = self.create_tab_wave()
        self.tab_reactive = self.create_tab_reactive()
        self.tab_reset = self.create_tab_reset()

        self.tabs.addTab(self.tab_static, "Static")
        self.tabs.addTab(self.tab_breathing, "Breathing")
        self.tabs.addTab(self.tab_wave, "Wave")
        self.tabs.addTab(self.tab_reactive, "Reactive")
        self.tabs.addTab(self.tab_reset, "Reset")

    def refresh_devices(self):
        self.device_combo.clear()
        devices = scan_razer_devices(debug_mode=self.debug_mode)
        if not devices:
            msg = "No Razer devices found."
            if self.debug_mode:
                msg += "\n\nDebug mode enabled. Check console output for raw HID device data."
                import logging
                logging.info("No supported devices found. Check logs for raw HID enumeration.")
            QMessageBox.warning(self, "Error", msg)
            return
        self.devices = devices
        for dev in devices:
            self.device_combo.addItem(f"{dev['name']} (PID: 0x{dev['pid']:04X})", dev)
        self.device_combo.setCurrentIndex(0)

    def get_selected_device(self):
        idx = self.device_combo.currentIndex()
        if idx < 0:
            return None
        return self.device_combo.itemData(idx)

    def create_tab_static(self):
        tab = QWidget()
        layout = QFormLayout(tab)
        self.static_spin_r = QSpinBox(); self.static_spin_r.setRange(0, 255); self.static_spin_r.setValue(255)
        self.static_spin_g = QSpinBox(); self.static_spin_g.setRange(0, 255); self.static_spin_g.setValue(255)
        self.static_spin_b = QSpinBox(); self.static_spin_b.setRange(0, 255); self.static_spin_b.setValue(255)
        layout.addRow("Red:", self.static_spin_r)
        layout.addRow("Green:", self.static_spin_g)
        layout.addRow("Blue:", self.static_spin_b)
        btn = QPushButton("Send Static Effect")
        btn.clicked.connect(self.send_static)
        layout.addRow(btn)
        return tab

    def send_static(self):
        device = self.get_selected_device()
        if not device:
            QMessageBox.warning(self, "Error", "No device selected.")
            return
        r = self.static_spin_r.value()
        g = self.static_spin_g.value()
        b = self.static_spin_b.value()
        extra = [r, g, b]
        pid = device['pid']
        if is_mouse_device(pid):
            led_id = MOUSE_SCROLL_WHEEL_LED
            effect_code = MOUSE_EFFECT_STATIC
            transaction_id = MOUSE_TRANSACTION_ID
            data_size = MOUSE_DATA_SIZE
            cmd_class = MOUSE_CMD_CLASS
            cmd_id = MOUSE_CMD_ID
        elif is_keyboard_device(pid):
            led_id = KBD_BACKLIGHT_LED
            effect_code = KBD_EFFECT_STATIC
            transaction_id = KBD_WIRED_TRANSACTION_ID if pid in [BW3PRO_WIRED_PID] else KBD_WIRELESS_TRANSACTION_ID
            data_size = KBD_DATA_SIZE
            cmd_class = KBD_CMD_CLASS
            cmd_id = KBD_CMD_ID
        else:
            QMessageBox.warning(self, "Error", "Unsupported device.")
            return
        args = build_arguments(effect_code, led_id, extra)
        report = construct_razer_report(transaction_id, cmd_class, cmd_id, data_size, args)
        if send_report_to_device(device, report, "Static Effect"):
            QMessageBox.information(self, "Success", f"Color set to ({r}, {g}, {b}).")
        else:
            QMessageBox.warning(self, "Error", "Failed to send effect.")

    def create_tab_breathing(self):
        tab = QWidget()
        layout = QFormLayout(tab)
        self.breathing_base_r = QSpinBox(); self.breathing_base_r.setRange(0, 255); self.breathing_base_r.setValue(255)
        self.breathing_base_g = QSpinBox(); self.breathing_base_g.setRange(0, 255); self.breathing_base_g.setValue(255)
        self.breathing_base_b = QSpinBox(); self.breathing_base_b.setRange(0, 255); self.breathing_base_b.setValue(255)
        layout.addRow("Base Red:", self.breathing_base_r)
        layout.addRow("Base Green:", self.breathing_base_g)
        layout.addRow("Base Blue:", self.breathing_base_b)
        self.breathing_extra_r = QSpinBox(); self.breathing_extra_r.setRange(0, 255); self.breathing_extra_r.setValue(0)
        self.breathing_extra_g = QSpinBox(); self.breathing_extra_g.setRange(0, 255); self.breathing_extra_g.setValue(0)
        self.breathing_extra_b = QSpinBox(); self.breathing_extra_b.setRange(0, 255); self.breathing_extra_b.setValue(0)
        layout.addRow("Breathing Red:", self.breathing_extra_r)
        layout.addRow("Breathing Green:", self.breathing_extra_g)
        layout.addRow("Breathing Blue:", self.breathing_extra_b)
        self.breathing_speed = QSpinBox(); self.breathing_speed.setRange(0, 255); self.breathing_speed.setValue(128)
        layout.addRow("Speed:", self.breathing_speed)
        btn = QPushButton("Send Breathing Effect")
        btn.clicked.connect(self.send_breathing)
        layout.addRow(btn)
        return tab

    def send_breathing(self):
        device = self.get_selected_device()
        if not device:
            QMessageBox.warning(self, "Error", "No device selected.")
            return
        base = [self.breathing_base_r.value(), self.breathing_base_g.value(), self.breathing_base_b.value()]
        extra_color = [self.breathing_extra_r.value(), self.breathing_extra_g.value(), self.breathing_extra_b.value()]
        speed = self.breathing_speed.value()
        extra = base + extra_color + [speed]
        pid = device['pid']
        if is_mouse_device(pid):
            led_id = MOUSE_SCROLL_WHEEL_LED
            effect_code = MOUSE_EFFECT_BREATHING
            transaction_id = MOUSE_TRANSACTION_ID
            data_size = MOUSE_DATA_SIZE
            cmd_class = MOUSE_CMD_CLASS
            cmd_id = MOUSE_CMD_ID
        elif is_keyboard_device(pid):
            led_id = KBD_BACKLIGHT_LED
            effect_code = KBD_EFFECT_BREATHING
            transaction_id = KBD_WIRED_TRANSACTION_ID if pid in [BW3PRO_WIRED_PID] else KBD_WIRELESS_TRANSACTION_ID
            data_size = KBD_DATA_SIZE
            cmd_class = KBD_CMD_CLASS
            cmd_id = KBD_CMD_ID
        else:
            QMessageBox.warning(self, "Error", "Unsupported device.")
            return
        args = build_arguments(effect_code, led_id, extra)
        report = construct_razer_report(transaction_id, cmd_class, cmd_id, data_size, args)
        if send_report_to_device(device, report, "Breathing Effect"):
            QMessageBox.information(self, "Success", "Breathing effect sent.")
        else:
            QMessageBox.warning(self, "Error", "Failed to send effect.")

    def create_tab_wave(self):
        tab = QWidget()
        layout = QFormLayout(tab)
        self.wave_speed = QSpinBox(); self.wave_speed.setRange(0, 255); self.wave_speed.setValue(128)
        layout.addRow("Speed:", self.wave_speed)
        self.radio_left = QRadioButton("Left -> Right")
        self.radio_right = QRadioButton("Right -> Left")
        self.radio_left.setChecked(True)
        radio_layout = QHBoxLayout()
        radio_layout.addWidget(self.radio_left)
        radio_layout.addWidget(self.radio_right)
        layout.addRow("Direction:", radio_layout)
        btn = QPushButton("Send Wave Effect")
        btn.clicked.connect(self.send_wave)
        layout.addRow(btn)
        return tab

    def send_wave(self):
        device = self.get_selected_device()
        if not device:
            QMessageBox.warning(self, "Error", "No device selected.")
            return
        speed = self.wave_speed.value()
        direction = 0 if self.radio_left.isChecked() else 1
        extra = [speed, direction]
        pid = device['pid']
        if is_mouse_device(pid):
            led_id = MOUSE_SCROLL_WHEEL_LED
            effect_code = MOUSE_EFFECT_WAVE
            transaction_id = MOUSE_TRANSACTION_ID
            data_size = MOUSE_DATA_SIZE
            cmd_class = MOUSE_CMD_CLASS
            cmd_id = MOUSE_CMD_ID
        elif is_keyboard_device(pid):
            led_id = KBD_BACKLIGHT_LED
            effect_code = KBD_EFFECT_WAVE
            transaction_id = KBD_WIRED_TRANSACTION_ID if pid in [BW3PRO_WIRED_PID] else KBD_WIRELESS_TRANSACTION_ID
            data_size = KBD_DATA_SIZE
            cmd_class = KBD_CMD_CLASS
            cmd_id = KBD_CMD_ID
        else:
            QMessageBox.warning(self, "Error", "Unsupported device.")
            return
        args = build_arguments(effect_code, led_id, extra)
        report = construct_razer_report(transaction_id, cmd_class, cmd_id, data_size, args)
        if send_report_to_device(device, report, "Wave Effect"):
            QMessageBox.information(self, "Success", "Wave effect sent.")
        else:
            QMessageBox.warning(self, "Error", "Failed to send effect.")

    def create_tab_reactive(self):
        tab = QWidget()
        layout = QFormLayout(tab)
        self.reactive_spin_r = QSpinBox(); self.reactive_spin_r.setRange(0, 255); self.reactive_spin_r.setValue(255)
        self.reactive_spin_g = QSpinBox(); self.reactive_spin_g.setRange(0, 255); self.reactive_spin_g.setValue(255)
        self.reactive_spin_b = QSpinBox(); self.reactive_spin_b.setRange(0, 255); self.reactive_spin_b.setValue(255)
        layout.addRow("Reaction Red:", self.reactive_spin_r)
        layout.addRow("Reaction Green:", self.reactive_spin_g)
        layout.addRow("Reaction Blue:", self.reactive_spin_b)
        self.reactive_duration = QSpinBox(); self.reactive_duration.setRange(0, 255); self.reactive_duration.setValue(50)
        layout.addRow("Duration:", self.reactive_duration)
        btn = QPushButton("Send Reactive Effect")
        btn.clicked.connect(self.send_reactive)
        layout.addRow(btn)
        return tab

    def send_reactive(self):
        device = self.get_selected_device()
        if not device:
            QMessageBox.warning(self, "Error", "No device selected.")
            return
        color = [self.reactive_spin_r.value(), self.reactive_spin_g.value(), self.reactive_spin_b.value()]
        duration = self.reactive_duration.value()
        extra = color + [duration]
        pid = device['pid']
        if is_mouse_device(pid):
            led_id = MOUSE_SCROLL_WHEEL_LED
            effect_code = MOUSE_EFFECT_REACTIVE
            transaction_id = MOUSE_TRANSACTION_ID
            data_size = MOUSE_DATA_SIZE
            cmd_class = MOUSE_CMD_CLASS
            cmd_id = MOUSE_CMD_ID
        elif is_keyboard_device(pid):
            led_id = KBD_BACKLIGHT_LED
            effect_code = KBD_EFFECT_REACTIVE
            transaction_id = KBD_WIRED_TRANSACTION_ID if pid in [BW3PRO_WIRED_PID] else KBD_WIRELESS_TRANSACTION_ID
            data_size = KBD_DATA_SIZE
            cmd_class = KBD_CMD_CLASS
            cmd_id = KBD_CMD_ID
        else:
            QMessageBox.warning(self, "Error", "Unsupported device.")
            return
        args = build_arguments(effect_code, led_id, extra)
        report = construct_razer_report(transaction_id, cmd_class, cmd_id, data_size, args)
        if send_report_to_device(device, report, "Reactive Effect"):
            QMessageBox.information(self, "Success", "Reactive effect sent.")
        else:
            QMessageBox.warning(self, "Error", "Failed to send effect.")

    def create_tab_reset(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        btn = QPushButton("Reset Effect")
        btn.clicked.connect(self.send_reset)
        layout.addWidget(btn)
        layout.addStretch()
        return tab

    def send_reset(self):
        device = self.get_selected_device()
        if not device:
            QMessageBox.warning(self, "Error", "No device selected.")
            return
        pid = device['pid']
        effect_code = 0x00
        if is_mouse_device(pid):
            led_id = MOUSE_SCROLL_WHEEL_LED
            transaction_id = MOUSE_TRANSACTION_ID
            data_size = MOUSE_DATA_SIZE
            cmd_class = MOUSE_CMD_CLASS
            cmd_id = MOUSE_CMD_ID
        elif is_keyboard_device(pid):
            led_id = KBD_BACKLIGHT_LED
            transaction_id = KBD_WIRED_TRANSACTION_ID if pid in [BW3PRO_WIRED_PID] else KBD_WIRELESS_TRANSACTION_ID
            data_size = KBD_DATA_SIZE
            cmd_class = KBD_CMD_CLASS
            cmd_id = KBD_CMD_ID
        else:
            QMessageBox.warning(self, "Error", "Unsupported device.")
            return
        args = build_arguments(effect_code, led_id, [])
        report = construct_razer_report(transaction_id, cmd_class, cmd_id, data_size, args)
        if send_report_to_device(device, report, "Reset Effect"):
            QMessageBox.information(self, "Success", "Reset effect sent.")
        else:
            QMessageBox.warning(self, "Error", "Failed to send reset effect.")