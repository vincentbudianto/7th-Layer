# Simple-Websocket-Server

Implementasi websocket server sederhana yang terbuat dari layer 4 dengan menggunakan TCP
socket dan tidak menggunakan HTTP server.

Referensi protokol websocket: https://tools.ietf.org/html/rfc6455

Fungsionalitas:
1. Handshake (opening & closing)
2. Framing (parsing & building)
3. Control frame (PING, PONG, CLOSE, dll)

## Kelompok Bambang
Terdiri dari:
1. 13517014 - Yoel Susanto
2. 13517059 - Nixon Andhika
3. 13517137 - Vincent Budianto

## Petunjuk Penggunaan Program
1. Jalankan server dengan menggunakan command:
```sh
$ python server.py
```
2. Jalankan ngrok
3. Untuk windows, buka ngrok.exe dan masukkan command (9001 merupakan port yang digunakan):
```sh
ngrok.exe http 9001
```
4. Untuk linux, buka ngrok.exe dan masukkan command (9001 merupakan port yang digunakan):
```sh
$ ./ngrok.exe http 9001
```
5. Copy URL yang didapat ke https://jarkom.tenshi.dev/submission. Contoh URL:
```sh
ws://0a3e2e87.ngrok.io/
```
6. Masukkan authenthication token yang dikirim ke email
7. Tunggu hasil dari submission

## Pembagian Tugas
| NIM      | Nama            | Apa yang dikerjakan          | Persentase kontribusi |
| -------- | --------------- | ---------------------------- | --------------------- |
| 13517014 | Yoel Susanto    | Websocket, server            | 50%                   |
| 13517059 | Nixon Andhika   | Doc, beautify code           | 25%                   |
| 13517137 | Vincent Budianto| Client test, handshake       | 25%                   |