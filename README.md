# home-vpn-watch

自宅ルーター（TP-Link Archer AX80）の **OpenVPN サーバーがインターネット側から到達できるか**を、
GitHub Actions から30分ごとに確認する。結果は Uptime Kuma が GitHub API 経由で参照する。

## なぜ必要か

Uptime Kuma は自宅 LAN 内（Mac mini）で動いている。このルーターは NAT ヘアピンを行わない
（Tailscale の `netcheck` が `HairPinning: false` と報告）ため、**LAN 内からは自分の WAN 側ポートを
検査できない**。また Uptime Kuma のポート監視は TCP 専用で、UDP である OpenVPN(1194) は扱えない。
そのため「家の外の足場」として GitHub Actions を使う。

## 判定方法

`scripts/openvpn_probe.py` が `P_CONTROL_HARD_RESET_CLIENT_V2` を UDP 1194 に送り、
サーバーからの `P_CONTROL_HARD_RESET_SERVER_V2`（opcode 8）を待つ。
応答が返れば次の3つが同時に確認できる。

1. WAN 側の UDP 1194 が開いている
2. ルーターの転送が生きている
3. OpenVPN サーバー本体が正常に応答している

UDP はパケットロスがあるため4回まで再試行する。

## 設定

- リポジトリ Secret `VPN_HOST` に接続先ホスト名（DDNS 名）を入れる。
  ワークフロー定義は公開されるが、Secret の値は公開されない。

## 監視されていないもの

- **WireGuard (UDP 51820)** — 不正パケットを無言破棄する仕様のため、外部からは
  「開いている」と「フィルタされている」を区別できない。判定するにはサーバー公開鍵が必要。
- 同じルーターの同じ WAN 経路を通るため、OpenVPN が外から届いていれば
  回線・ルーター側は健全だと推測はできる（証明ではない）。

## Uptime Kuma 側

`HTTP(s) - Jsonクエリ` モニターで以下をポーリングする。

- URL: `https://api.github.com/repos/mino-code/home-vpn-watch/actions/workflows/vpn-check.yml/runs?per_page=1&status=completed`
- Json クエリ: `workflow_runs[0].conclusion`
- 期待値: `success`

パブリックリポジトリなので認証は不要。

### 既知の限界

Actions の実行自体が止まると、最後の成功結果が残り続けて**偽の緑**になりうる。
`keepalive.yml` で自動停止は防いでいるが、この方式は「チェッカーの停止」を検知できない。
