# Raspberry Pi 유선 고정 IP 설정 (NetworkManager 기반)

**Raspberry Pi OS Bookworm (2023 이후 버전)** 기준
기존의 `/etc/dhcpcd.conf` 대신 **NetworkManager**가 네트워크를 관리합니다.
따라서 고정 IP 설정은 `nmcli` 명령어를 통해 진행해야 합니다.

---

## 환경 정보

| 항목            | 값                            |
| --------------- | ----------------------------- |
| 장치            | Raspberry Pi 5                |
| 운영체제        | Raspberry Pi OS (Bookworm)    |
| 연결 방식       | 유선 LAN (eth0)               |
| 서버 장치       | Jetson Orin / AGX             |
| 통신 방식       | Flask-SocketIO (Port: `5002`) |
| Jetson Orin IP  | `192.168.0.20`                |
| Raspberry Pi IP | `192.168.0.3x`                |

---

## 1. 현재 네트워크 상태 확인

먼저 NetworkManager가 관리 중인 인터페이스를 확인합니다.

```bash
nmcli device status
```

예시 출력:

```
DEVICE  TYPE      STATE      CONNECTION
eth0    ethernet  connected  Wired connection 1
wlan0   wifi      disconnected  --
```

만약 `eth0`가 `unavailable` 상태라면 아래 명령으로 활성화합니다.

```bash
sudo nmcli device set eth0 managed yes
sudo nmcli device connect eth0
```

---

## 2. 연결 이름 확인

`STATE`가 `connected`인 행의 **CONNECTION 이름**을 확인합니다.
(보통 `"Wired connection 1"` 또는 `"유선 연결 1"` 형태)

```bash
nmcli con show
```

---

## 3. 고정 IP 수동 설정

다음 명령어를 입력하여 라즈베리파이에 IP를 수동으로 지정합니다.

```bash
sudo nmcli con mod "Wired connection 1" \
  ipv4.method manual \
  ipv4.addresses 192.168.0.3x/24
```

| 설정 항목         | 설명                          |
| ----------------- | ----------------------------- |
| `192.168.0.3x/24` | 라즈베리파이에 부여할 고정 IP |

---

## 4. 자동 연결 활성화

재부팅 시 자동으로 연결되도록 설정합니다.

```bash
sudo nmcli con mod "Wired connection 1" connection.autoconnect yes
```

---

## 5. 연결 재시작

변경된 설정을 반영하기 위해 네트워크를 재시작합니다.

```bash
sudo nmcli con down "Wired connection 1"
sudo nmcli con up "Wired connection 1"
```

---

## 6. IP 설정 확인

```bash
ip addr show eth0
```

예시 출력:

```
2: eth0: <BROADCAST,MULTICAST,UP,LOWER_UP> mtu 1500 qdisc fq_codel state UP group default qlen 1000
    inet 192.168.0.31/24 brd 192.168.0.255 scope global eth0
       valid_lft forever preferred_lft forever
```

---

## 7. Jetson Orin과 통신 확인

Jetson Orin(서버)의 IP가 `192.168.0.20`이라면,
Raspberry Pi에서 다음 명령으로 확인할 수 있습니다.

```bash
ping 192.168.0.20
```

Orin에서도 확인 가능합니다.

```bash
ping 192.168.0.3x
```

응답이 정상적으로 오면 통신 성공.

---

## 정리

| 항목            | 값             |
| --------------- | -------------- |
| 라즈베리파이 IP | `192.168.0.31` |
| Jetson Orin IP  | `192.168.0.20` |
| 포트 번호       | `5002`         |
| 통신 방식       | Flask-SocketIO |
| 네트워크 방식   | LAN (유선)     |

---

**작성자:** 김민석
**프로젝트:** Parking Control System
**목적:** Jetson Orin ↔ Raspberry Pi 간 안정적인 유선 통신 환경 구축
**버전:** Raspberry Pi OS Bookworm (NetworkManager 기반)
