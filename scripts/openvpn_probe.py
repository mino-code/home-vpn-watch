#!/usr/bin/env python3
"""外部から OpenVPN サーバーへハンドシェイクを1発投げ、応答の有無で到達性を判定する。

成功条件: P_CONTROL_HARD_RESET_SERVER_V2 (opcode 8) が返ってくること。
これが返れば「WAN ポートが開いている」「転送が生きている」「サーバーが応答している」の
3つが同時に確認できる。UDP はパケットロスするので数回試行する。
"""
import os
import socket
import struct
import sys

OPCODE_HARD_RESET_CLIENT_V2 = 7
OPCODE_HARD_RESET_SERVER_V2 = 8
ATTEMPTS = 4
TIMEOUT = 3.0


def probe(host, port):
    """1回だけ試行する。成功なら (True, 説明)、失敗なら (False, 説明) を返す。"""
    session_id = os.urandom(8)
    # opcode を上位5bit、key_id を下位3bit に詰める
    packet = bytes([OPCODE_HARD_RESET_CLIENT_V2 << 3]) + session_id + b"\x00" + struct.pack(">I", 1)

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.settimeout(TIMEOUT)
    try:
        sock.sendto(packet, (host, port))
        data, _ = sock.recvfrom(1024)
    except socket.timeout:
        return False, "無応答（ポート閉鎖・フィルタ・サーバー停止のいずれか）"
    except ConnectionRefusedError:
        return False, "ICMP port unreachable（待ち受けなし）"
    except socket.gaierror as exc:
        return False, f"名前解決に失敗: {exc}"
    except OSError as exc:
        return False, f"ソケットエラー: {exc}"
    finally:
        sock.close()

    if not data:
        return False, "空の応答"
    opcode = data[0] >> 3
    if opcode == OPCODE_HARD_RESET_SERVER_V2:
        return True, f"OpenVPN 応答あり（{len(data)} バイト, opcode={opcode}）"
    return False, f"OpenVPN 以外の応答（opcode={opcode}）"


def main():
    if len(sys.argv) != 3:
        print("usage: openvpn_probe.py <host> <port>", file=sys.stderr)
        return 2
    host, port = sys.argv[1], int(sys.argv[2])
    if not host:
        print("ホスト名が空です。VPN_HOST シークレットが設定されているか確認してください。", file=sys.stderr)
        return 2

    for attempt in range(1, ATTEMPTS + 1):
        ok, detail = probe(host, port)
        print(f"試行 {attempt}/{ATTEMPTS}: {detail}")
        if ok:
            print("結果: 到達可能")
            return 0
    print("結果: 到達不可", file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main())
