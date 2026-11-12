# Q-Pass (qr_commu) 内容把握メモ

Qiita 記事執筆・リモート公開に向けた現状整理。
調査日: 2026-08-12 / 対象コミット: `bea2788` (main)

---

## 1. プロジェクト概要

**Q-Pass (`qr_commu`)** — ネットワークを一切使わず、**画面に連続表示した QR コードを別 PC の Web カメラで読み取る**ことでファイルを転送するツール。エアギャップ環境向けの片方向データ転送。

| 項目 | 内容 |
| --- | --- |
| リモート | `https://github.com/kaze-uta/Q-Pass.git` |
| 公開状態 | **private**（GitHub API が 404 を返す） |
| ライセンス | MIT |
| 言語 | Python 3.x |
| 追跡ファイル | 6 個（`.gitignore` / `LICENSE` / `README.md` / `receive/function.py` / `requirements.txt` / `sent/main.py`） |

### 依存ライブラリ

| 用途 | パッケージ |
| --- | --- |
| QR コード生成 | `qrcode` |
| 画像処理 | `Pillow` |
| 画面表示・カメラ入力 | `opencv-python` |
| QR コードデコード | `pyzbar` |
| 配列処理 | `numpy` |

---

## 2. リポジトリの状態

- `main` と `origin/main` は同期済み。作業ツリーもクリーン。
- `develop` は `main` に対して `sent/a.jpg`（テスト画像）が 1 枚多いだけ。実装差分なし。

### コミット履歴

```
bea2788 chore: remove test image *.jpg from tracking
19b2e3a Merge branch 'develop'
3da2b00 chore: remove generated files from tracking
cac94f4 fix: correct termination logic in QR code reading loop
c81ca05 refactor: switch encoding from binary to Base64
c362a00 feat: parallelize QR generation and display with threading, ...
bbad37c Initial commit: offline file transfer via QR code sequence
```

記事のストーリーとして使える流れ:
バイナリ直載せ → **Base64 化**（`c81ca05`）→ **生成と表示のスレッド並列化**（`c362a00`）→ **終端判定の修正**（`cac94f4`）。

---

## 3. 転送プロトコル

```
[送信側 PC]                          [受信側 PC]
 ファイル                             Web カメラ
   │ CAPACITY バイトごとに分割          │ pyzbar でデコード
   │ 各チャンクを Base64 化             │
   ▼                                   ▼
 QR を 2 秒ごとに順次表示  ──カメラ──▶  順番に読み取り
   1 枚目 : 拡張子 (Base64)             1 枚目 : 拡張子を取得
   2 枚目〜: データ本体 (Base64)         データを get.<拡張子> に追記
   最終枚 : "bGFzdA==" (= "last")       終端マーカーで終了
```

- **1 枚目**: 送信ファイルの拡張子（`txt`, `png` など）を Base64 化
- **2 枚目以降**: ファイルデータを `CAPACITY` バイトずつに分割したチャンクを Base64 化
- **最終枚**: `base64.b64encode(b"last")` = `bGFzdA==` を終端マーカーとして表示

**シーケンス番号もチェックサムも無い**、表示タイマー依存の同期方式。

---

## 4. 送信側 `sent/main.py`

| 関数 | 役割 |
| --- | --- |
| `getfile()` | バイナリ読み込み＋`os.path.splitext` で拡張子取得 |
| `create_qr()` | `ERROR_CORRECT_H`（最高冗長度）、`fit=True` で version 自動拡張、`qrcode{n}.png` として CWD に保存 |
| `show_qr()` | 3 秒待機後、`qrcode1.png` から順に 700x700 にリサイズして `cv2.imshow`、`waitKey(2000)` で 2 秒ごと切替 |
| `sent_qr()` | 拡張子 QR → データ QR 群 → `last` QR を順に生成 |
| `delete_qr()` | 表示済み PNG の削除（**呼び出しがコメントアウト中**） |

### 設計上のポイント

- **2 スレッド並列**（`c362a00` の主眼）: 生成スレッド `sent_qr` と表示スレッド `show_qr` を同時に走らせ、全生成の完了を待たずに表示を開始する。**3 秒のヘッドスタートが唯一のバッファ**で、生成が表示に追い抜かれると早期終了する。
- **終端判定**: `cv2.imread` が `None` を返す → `cv2.resize` が例外 → `except` で `break`（`sent/main.py:48`）。ファイルの有無を例外でハンドリングしている。
- チャンク分割ループ `while long > CAPACITY * (i - 1)` は境界条件込みで正しく動作する（`long=200, CAP=200` でも `long=201` でも過不足なし）。`while ... else` で終端マーカーを生成。

### 主要定数

| 定数 | 場所 | 実値 | 説明 |
| --- | --- | --- | --- |
| `CAPACITY` | `sent/main.py:12` | **200** | QR 1 枚に詰めるバイト数。Base64 で 4/3 に膨らむので実質 ~268 文字 |
| `cv2.waitKey(2000)` | `sent/main.py:45` | 2000 ms | 1 枚あたりの表示時間 |

---

## 5. 受信側 `receive/function.py`

- `cv.VideoCapture(1)` — **カメラ index は 1 固定**（外付けカメラ前提）
- `pyzbar.decode()` で毎フレーム走査、検出枠を `cv.polylines` で青く描画
- 直前フレームのデータ（`check`）と比較する**重複排除**
- `bGFzdA==` を検出したら `j += 1` → 内側 `for` を `break` → 外側 `if j >= 1` で `break`（`cac94f4` の修正箇所）
- `open(f"get.{extension}", "ab")` で追記しながら復元
- 拡張子 QR のスキップは、初回書き込み時に `i == 1` なら `pass` する暗黙のカウンタ制御

---

## 6. 実装のクセ・既知の弱点

記事では正直に書くと逆に価値が出るポイント。

### 優先度: 高

1. **README と実装の乖離**
   README は `CAPACITY = 2800` と記載しているが、`sent/main.py:12` の実値は **200**。記事化前に修正するか、記事内で言及が必要。

2. **連続する同一チャンクが黙って落ちる**
   重複排除が「直前フレームとの比較」のみ（`receive/function.py:31`, `:51`）。
   ゼロ埋め領域など**同じ内容のチャンクが 2 枚連続すると 2 枚目が捨てられ、ファイルが壊れる**。バイナリ転送における実質的な最大の弱点。

3. **生成済み PNG が消えない**
   `delete_qr()` の呼び出しが `sent/main.py:46` でコメントアウト。前回実行の `qrcodeN.png` が残るため、**次回の枚数が少ないと古い QR を表示してしまう**。

### 優先度: 中

4. **`get.*` への追記モード**
   `"ab"` で開くため、既存ファイルがあると前回分の後ろに連結される。

5. **`barcode.data[0] != ""` が実質ノーオペ**
   `bytes` の添字は `int` なので `str` との比較は常に True（`receive/function.py:27`, `:31`）。かつ空データで `IndexError`。

6. **`.gitignore` に `*.txt`**
   `requirements.txt` は追跡済みなので現状は無害だが、新規の `.txt` は追加されない罠。

### 優先度: 低

7. 取りこぼし時の**リトライ・整合性検証が無い**（シーケンス番号もハッシュも無し）
8. 受信側で `cap.release()` が未呼び出し。終端パスで `destroyAllWindows()` も通らない
9. `getfile()` はドットを含まないファイル名で `UnboundLocalError`
10. 送信側でスレッドの `join()` をしていない（非デーモンなので実害はない）

---

## 7. 公開に向けたタスク

- [ ] `gh auth login` で GitHub CLI を認証（未認証状態）
- [ ] 既存 private リポジトリ `kaze-uta/Q-Pass` を **public に切り替え**（新規作成ではない）
- [ ] README の `CAPACITY` 記述を実値 200 に修正（または実装を 2800 に合わせる）
- [ ] 公開前に弱点 2・3 を修正するか、「今後の課題」として残すかを判断

## 8. Qiita 記事の方向性（未決定）

- **案 A: 「作ってみた」寄り** — エアギャップという動機、2 台並べた実際の絵、動くまでの試行錯誤を主軸に
- **案 B: 「プロトコル解説」寄り** — Base64 化の理由、チャンク分割の境界条件、生成/表示の並列化、終端検出の設計を主軸に

いずれの場合も 6 章の「弱点」を **今後の課題**セクションとして正直に載せると記事の信頼性が上がる。
