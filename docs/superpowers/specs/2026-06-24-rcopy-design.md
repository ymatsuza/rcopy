# rcopy 設計書（解決アプリ第4号：除外付きクロスプラットフォーム・コピー）

- 日付: 2026-06-24
- ステータス: 承認済み（brainstorming にて候補・スコープ・名前・除外セマンティクスを確定）
- 種別: アプリ設計仕様

> プロジェクト名 `rcopy`（= recursive copy with excludes。rsed・rcaudit・rcmd と同じ r- ファミリー）。コマンド名も `rcopy`。`rcp` は旧 remote-copy コマンドと衝突するため避ける。

## 0. 背景（なぜこれを作るか）

サブプロジェクト (A) `kadai-radar` の候補 **[75]「日常のファイル操作CLIの隙間を埋める小道具群」**（freq 4 / mentions 4 ＝ 全候補で最強の需要シグナル）。ただしこれは寄せ集めなので、4つの出典スレッドを精読して**未充足の1つに分割**した：

| サブニーズ | スレ反応 | 競合 | 判定 |
|---|---|---|---|
| **除外付きの再帰コピー**（Win `Copy-Item` に exclude が無い/壊れる） | ツール告知系 | robocopy(Win専用/古い構文)・rsync(Windows標準に無し/複雑)・Cpr(個人作1本) | **唯一の未飽和・クロスプラットフォーム隙間** |
| 万能解凍 | 5up/7c | ouch(Rust/CP)・7zip・atool | 飽和 |
| 高速 cd | 0up/26c | zoxide/autojump/CDPATH | 飽和 |
| FSブラウザ | 2up/3c | ranger/nnn/lf/broot/ncdu | 飽和＋TUI（型外） |

→ 4つ中3つは既存ツールで飽和。残る隙間は **「除外付きの再帰コピー」** だけ。これは本物の痛点：**Windows の `Copy-Item -Exclude` は `-Recurse` と組むとサブディレクトリに効かない**ことで有名、`robocopy` は Windows 専用＆ `/XF /XD` の古い構文、`rsync --exclude` は Windows 標準に無く複雑。

→ **「gitignore 風の除外/包含パターンが全OSで同一に効く、焦点特化の再帰コピー CLI。`--dry-run` で実行前プレビュー」** を作る。rsync/robocopy/Copy-Item 不要、純Python・ローカル完結・純関数コアでテスト完全検証。

## 1. ゴールと非ゴール

**ゴール（v1）**
- 1つ以上の SRC を DST へ**再帰コピー**でき、**gitignore 風の `--exclude` / `--include`** で含める/除くを制御できる（全OS同一挙動）。
- `--exclude-from FILE` で `.gitignore` 風のパターンファイルを読める。
- `--dry-run` でコピー予定の `src -> dst` 一覧を出すだけ（書き込みなし）。Windows ユーザーの「壊れず除外できるか不安」を解消。
- 既定は cp 互換で上書き。`--no-clobber` で既存をスキップ。`--no-recurse` でトップレベルのみ。`-v` で各コピーを表示。
- ローカル完結（ネットワーク不要）。純関数コア（パターンマッチ・コピー計画）でテスト検証、実機で実証。

**非ゴール（v1、後段）**
- 同期（rsync 的な差分転送・削除ミラー `--delete`）。コピーに集中。
- リモートコピー（SSH/ネットワーク）。ローカルのみ。
- 移動（mv）・ハードリンク・シンボリックリンクの特別扱い（v1 はシンボリックリンクを**辿らずそのままコピー**＝ループ回避）。
- 進捗バー・並列コピー・TUI。
- 完全な gitignore 仕様の再現（`!` の親ディレクトリ除外時の再包含など難所は割り切る。§5・§11 参照）。

## 2. 設計判断

### 2.1 パターン = gitignore 風 glob（独自・純関数）

ユーザーが期待するのは「`node_modules` を除く」「`*.log` を除く」「`build/` を除く」。これを **gitignore 風セマンティクス**（§5）で実装する。追加依存なし（stdlib `fnmatch` ではディレクトリ境界・`**` を扱えないため、glob→正規表現の小さな変換を自前で持つ＝純関数・最重点テスト）。

- 却下 A: `pathlib.PurePath.match`（`**` やディレクトリ・anchor の挙動が不足/環境差あり）。
- 却下 B: 外部の `pathspec`（gitignore ライブラリ。依存を増やす。型に反する）。v1 は必要十分な部分集合を自前実装。

### 2.2 上書きは cp 互換（既定で上書き、`--no-clobber` で回避）

コピーツールの最小驚き原則に従い `cp` 互換（既定上書き）。安全側の `--dry-run` を併設。`--no-clobber` で既存ファイルをスキップ。

### 2.3 クロスプラットフォーム

パターンはパス区切りを `/` に正規化して照合。コピーは stdlib `shutil.copy2`（メタデータ保持）＋ `os.walk`。Windows/macOS/Linux で同一挙動。シンボリックリンクは辿らずそのままコピー（無限ループ回避）。

## 3. CLI 仕様

```
rcopy SRC... DST  [-e/--exclude PAT]...  [-i/--include PAT]...  [--exclude-from FILE]...
                  [--dry-run]  [-v/--verbose]  [--no-recurse]  [--no-clobber]
rcopy version
```

- **SRC... DST** … 最後の引数が DST。解決規則は `cp -r` 互換：
  - **単一ディレクトリ SRC・DST が存在しない** → DST を SRC の**内容のミラー**として作成（`rcopy proj backup` → `backup/` が proj の中身）。
  - **単一ディレクトリ SRC・DST が既存ディレクトリ** → SRC を `DST/<basename(SRC)>/` 配下へコピー（`rcopy proj out`（out 既存）→ `out/proj/...`）。
  - **複数 SRC**（or ディレクトリ SRC を含む混在） → DST は**ディレクトリ扱い**（無ければ作成）、各 SRC を `DST/<basename>` 配下へ。DST が既存**ファイル**なら `Exit(2)`。
  - **単一ファイル SRC** → DST が既存ディレクトリならその中へ（`DST/<basename>`）、そうでなければ DST 名でコピー。
  - 相対パス（`relpath`）はパターン照合用に各 SRC ルート基準で算出する。
- **`-e/--exclude PAT`** … 除外パターン（繰り返し可）。§5 のセマンティクス。
- **`-i/--include PAT`** … 再包含パターン（繰り返し可）。除外より優先（include に一致するファイルは除外に一致しても必ずコピー。ただし除外ディレクトリの剪定により辿られない子孫は対象外＝§5・§11）。
- **`--exclude-from FILE`** … パターンファイル（1行1パターン、`#` 行頭コメント・空行無視）。繰り返し可。
- **`--dry-run`** … コピーせず `src -> dst` を列挙。終了コード 0。
- **`-v/--verbose`** … コピーした各ファイルを表示。
- **`--no-recurse`** … ディレクトリはトップレベルのファイルのみコピー（サブディレクトリに降りない）。
- **`--no-clobber`** … 既存の宛先ファイルを上書きせずスキップ（スキップは失敗ではない）。
- **`version`** … バージョン表示。

**終了コード**（rsed/rcaudit/rcmd 規約に一致）: `0`=正常（コピー0件でも SRC が有効なら 0）、`1`=一部コピー失敗（個々の I/O エラーは収集して継続、最後に 1）、`2`=使い方/入力不正（引数不足・SRC が存在しない・複数 SRC なのに DST がファイル等）。

## 4. コンポーネント（単一責務・テスト可能）

```
rcopy/
  pyproject.toml
  src/rcopy/
    __init__.py        # __version__
    errors.py          # RcopyError（単一の利用者向け例外）
    patterns.py        # Matcher: compile/match（純関数・最重点）
    plan.py            # Op(dataclass), build_plan（walk＋剪定＋include 上書き）
    copy.py            # execute（I/O：mkdir・copy2・no-clobber・dry-run・エラー収集）
    cli.py             # typer 配線（引数解釈・終了コード）
  tests/
    test_patterns.py test_plan.py test_copy.py test_cli.py
  README.md
```

- **patterns.py**
  - `match_pattern(pattern: str, relpath: str, is_dir: bool) -> bool`（純）。§5 の規則。`relpath` は `/` 区切り。
  - `Matcher`（excludes/includes を保持）: `is_excluded(relpath, is_dir) -> bool` / `is_included(relpath, is_dir) -> bool`（いずれかの該当パターンに一致）。
  - `parse_pattern_file(text: str) -> list[str]`（`#` コメント・空行除去・前後空白 strip）。
  - `_glob_to_regex(glob: str) -> str`（`*`→`[^/]*`、`**`→`.*`、`?`→`[^/]`、その他はエスケープ。境界アンカー付き）。純・テスト対象。

- **plan.py**
  - `Op`（dataclass）: `src: Path, dst: Path`。
  - `build_plan(sources: list[Path], dst: Path, matcher: Matcher, recurse: bool) -> list[Op]`。各 source を `os.walk`（topdown）で辿り、**除外ディレクトリは降りない（剪定）**、ファイルは `is_excluded and not is_included` で除外。`relpath` は各 source ルート基準。単一ファイル SRC や複数 SRC、DST がディレクトリ/ファイルの解決もここ（DST 解決は CLI から渡された方針に従う）。純度高め（FS walk のみ、書き込みなし）。

- **copy.py**
  - `Result`（dataclass）: `copied: int, skipped: int, errors: list[tuple[Path, str]]`。
  - `execute(ops: list[Op], dry_run: bool, no_clobber: bool, verbose: bool, echo) -> Result`。`dry_run` は `src -> dst` を echo するのみ。実行時は親 `mkdir(parents=True, exist_ok=True)`→`no_clobber` かつ dst 存在ならスキップ→`shutil.copy2`。個々の `OSError` は `errors` に収集して継続。

- **cli.py**（typer, `add_completion=False`）… SRC/DST 解析（最後を DST に）、SRC 存在チェック（無ければ `Exit(2)`）、複数 SRC で DST がファイル→`Exit(2)`、`--exclude-from` を読み込んで excludes に連結、`Matcher` 構築、`build_plan`→`execute`、`Result.errors` があれば `Exit(1)`。日本語ヘルプ。

## 5. パターンセマンティクス（v1 の定義）

照合は **source ルートからの相対パスを `/` 区切りに正規化**して行う。

- 末尾 `/`（例 `build/`）… **ディレクトリのみ**に一致（`is_dir` 真）。照合時に末尾 `/` を外す。
- パターンに `/` を**含まない**（例 `*.log`・`node_modules`）… **任意の階層の basename**に一致（gitignore 挙動）。`relpath` の**いずれかのパスセグメント**が glob 一致すれば真。
- パターンに `/` を**含む**（例 `src/*.tmp`・`/dist`）… `relpath` 全体に**アンカー**して一致。先頭 `/` は source ルート固定（外して全体一致）。先頭 `/` なしで `/` を含む場合も relpath 全体に一致を試みる。
- glob: `*`=`/` 以外の任意、`**`=ディレクトリ跨ぎ任意、`?`=`/` 以外の1文字。
- **ディレクトリ剪定**: あるディレクトリ relpath が除外に一致したら、その配下は walk しない（＝子孫すべて除外）。これにより `node_modules` 1つで配下全体が消える。
- **include 上書き**: ファイルが除外に一致しても include に一致すれば**コピーする**。ただし上記の剪定で辿られないディレクトリ配下のファイルは（walk されないため）対象にならない＝gitignore 同様の割り切り（§11）。

## 6. コピー実行（v1 の定義）

- 宛先の親ディレクトリは `mkdir(parents=True, exist_ok=True)` で用意。
- 既定は上書き（`shutil.copy2` でメタデータ＝更新時刻/権限を保持）。`--no-clobber` のとき dst 既存なら**スキップ**（`Result.skipped++`、失敗ではない）。
- `--dry-run` は `src -> dst` を1行ずつ表示し**書き込まない**。
- 個々のファイルの `OSError`（権限・読めない等）は `Result.errors` に `(src, message)` を収集して**他を継続**、最後に終了コード 1。
- シンボリックリンクは辿らずそのままコピー（`shutil.copy2` は既定でリンク先をコピー＝中身コピー。ループ回避のためディレクトリ walk では `followlinks=False`）。

## 7. エラー処理

| 箇所 | 方針 |
|------|------|
| 引数不足（SRC か DST が無い） | `RcopyError` を stderr、終了コード 2。 |
| SRC が存在しない | stderr に明示、終了コード 2。 |
| 複数 SRC（or ディレクトリ SRC）なのに DST が既存ファイル | stderr に明示、終了コード 2。 |
| `--exclude-from FILE` が読めない | stderr に明示、終了コード 2。 |
| 個々のファイルのコピー失敗 | `Result.errors` に収集し継続、最後に終了コード 1。 |
| 除外で対象 0 件 | 正常（終了コード 0、`-v` 時に「copied 0」を表示）。 |

## 8. テスト戦略（TDD・rcmd/rcaudit 並みの密度 ~45+）

- **patterns**: `match_pattern` を網羅 — `*.log`（任意階層 basename）、`**/*.tmp`、`node_modules`（dir 名どこでも）、`build/`（ディレクトリのみ）、アンカー `/dist`・`src/*.py`、`?`、`/` 含む/含まないの差。`_glob_to_regex` の単体。`Matcher.is_excluded/is_included`（複数パターン・include 上書き）。`parse_pattern_file`（コメント/空行/空白）。
- **plan**: 一時ディレクトリのツリーで `build_plan` — 除外ディレクトリの剪定（配下が消える）、`*.log` 除外、include 再包含、`--no-recurse`、複数 SRC、単一ファイル SRC、DST 解決（既存ディレクトリ内 vs 新規名）、relpath が source ルート基準。
- **copy**: 一時ディレクトリで `execute` — 実際にコピーされる/中身一致、`--dry-run` は書き込まない、`--no-clobber` は既存をスキップ・新規はコピー、`copy2` でメタデータ保持、コピー失敗（読めない src をモック）で `errors` 収集・継続。
- **cli**: `CliRunner` ＋ 一時ディレクトリ。除外が end-to-end で効く、`--dry-run` 出力、`--exclude-from`、終了コード（SRC 無し=2・複数SRC+ファイルDST=2・一部失敗=1・正常=0）、`version`。

## 9. 技術スタック

Python 3.11+ / uv / typer / pytest。**実行時依存は typer のみ**（コピー=stdlib `shutil`/`os`、パターン=自前 glob→regex、すべて stdlib）。ネットワーク不要・ローカル完結・クロスプラットフォーム（Windows/macOS/Linux）。ビルドは hatchling、`[project.scripts] rcopy = "rcopy.cli:app"`、pytest `pythonpath=["src"]`、`testpaths=["tests"]`。

## 10. 実装マイルストーン（計画フェーズ入力）

1. 足場（pyproject, パッケージ, `uv sync`）
2. `errors.py` ＋ `__init__.py`
3. `patterns.py`（`_glob_to_regex`・`match_pattern`・`Matcher`・`parse_pattern_file`）TDD
4. `plan.py`（`Op`・`build_plan`：walk＋剪定＋include）TDD
5. `copy.py`（`execute`：dry-run・no-clobber・copy2・エラー収集）TDD
6. `cli.py`（typer 配線・SRC/DST 解決・終了コード）＋ スモーク
7. README ＋ 実機検証（実 Windows で除外コピー・`--dry-run`・`--exclude-from`・`--no-clobber`）

## 11. 既知の割り切り

- gitignore 仕様の**完全再現はしない**。特に「除外ディレクトリ配下のファイルを `--include` で再包含」は剪定により walk されないため不可（gitignore も同様の制約）。v1 は実用上の大多数（`node_modules`/`*.log`/`build/` を除く、特定拡張子を再包含）に最適化。
- 同期（差分・削除ミラー）・移動・リモートコピーは非対象（コピーに集中）。
- シンボリックリンクは中身コピー（辿らず walk＝ループ回避）。リンクとして保持するオプションは後段。
- 競合（個人作 Cpr 等）は存在するが、**全OS同一の gitignore 風除外＋`--dry-run`＋依存ゼロ（typer のみ）** で差別化。Windows の `Copy-Item -Recurse -Exclude` 破綻・`robocopy` の Windows 専用/古構文・`rsync` の非Windows/複雑を一括で回避する点が価値。
