
# ⚙️ micro-ROS ESP-IDF Project Generator

A powerful CLI tool to **scaffold micro-ROS node code for ESP32** using the ESP-IDF framework. Automatically generates publishers, subscribers, services, clients, and timers — so you can focus on logic instead of boilerplate.

---

## 🚀 Features

* 🧠 Intelligently prompts for topics/services/timers
* 🔄 Auto-generates all `rclc_*` setup and callback boilerplate
* ⚙️ Supports **QoS** configuration (reliability)
* 🧩 Compatible with **ESP-IDF** + **micro-ROS** setup
* 📁 Populates and modifies `main.c` in a predefined template project
* 🧪 Easy to integrate with existing firmware

---

## 📦 Prerequisites

* Python 3.7+
* Git
* ESP-IDF and `idf.py` set up
* `micro_ros_espidf_component` cloned or installed

Install required Python packages:

```bash
pip install GitPython
```

---


## 🧰 Usage

Start the interactive wizard to generate a new micro-ROS project:

```bash
python3 main.py
```

### What It Does:

1. Asks for your ROS 2 distro
2. Asks project location
3. Asks project name
4. Lets you pick your desired:

   * Publishers (with message types & QoS)
   * Subscribers
   * Services
   * Clients
   * Timers (with callback frequency)
5. Generates:

   * All variable declarations
   * All `rclc_*` initializations
   * Callback function stubs
   * Properly linked `main.c` file in a copy of `uRosTemplet`

---

## 📷 Example Output

Example generated code for a publisher:

```c
RCCHECK(rclc_publisher_init_best_effort(
    &battery_publisher,
    &node,
    ROSIDL_GET_MSG_TYPE_SUPPORT(std_msgs, msg, Float32),
    "battery"
));

```

---

## 🛠️ Customization

You can extend or modify:

* `rclc_templet_init.json`: to change code generation structure
* `uRosTemplet/`: your base ESP-IDF micro-ROS project
* `main.py`: to tweak logic or add new interfaces (like parameters or actions)

---

## 🤝 Contributing

Contributions welcome! If you find bugs or want new features:

1. Open an issue or PR
2. Describe your use case or proposed change

## 🧪 TODO

* [ ] Add support for **ROS 2 Parameters**
* [ ] Implement **automatic variable assignments examples** for:

  * Subscribers
  * Publishers
  * Services
  * Clients
* [ ] Improve the **interactive CLI interface** for better usability
* [ ] Support for embeddedrtps


---

## 📝 License

Apache License 2.0
