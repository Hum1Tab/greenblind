# Greenblind

**PRのどの変更を消しても、テストが通ってしまうか。**

コミット済みコードのコピーで変更を一箇所ずつ戻し、同じコマンドを繰り返し実行します。元の作業ファイルは変更しません。モデル・APIキー・実行時の外部Pythonパッケージは不要です。

```sh
git clone https://github.com/Hum1Tab/greenblind.git
cd greenblind
python -m greenblind demo
```

Python 3.11以上とGitが必要です。`.greenblind/demo/report.html` を開くと実際の検証結果を確認できます。デモは2つの境界値修正を含み、そのうち1つしかテストされていない例です。

別のリポジトリで使う場合:

```sh
python -m greenblind check --repo /path/to/project --base HEAD~1 --include "src/*" -- python -m unittest discover -s tests
```

`--include` に検証する実装ファイルを明示してください。テストや設定ファイルまで戻さないように、必要に応じて `--exclude` を指定します。未コミットの変更は対象外です。

- `unnoticed`: 変更を戻してもコマンドが終了コード0で完了。
- `rejected`: 変更を戻すと同じ非0の終了コードで完了。
- `unstable`: 繰り返しで終了コードが変化。
- `inconclusive`: タイムアウト、起動失敗など。

`unnoticed` はテスト不足の手がかりですが、適切なリファクタリングの場合もあります。コードを削除してよい証明ではありません。`rejected` には構文エラーやビルド失敗も含まれ、バグを検出した証明ではありません。

毎回、追跡済みファイルだけの新しいコピーで実行します。依存関係は自動インストールしません。コマンドは利用者と同じ権限・環境変数で動くため、信頼できるコードで利用してください。サンドボックス機能はありません。

HTML・JSON・Markdownのレポートを生成します。レポートにはソースコードの抜粋とコマンド引数が含まれます。詳細な制約やCI連携は [English README](README.md) を参照してください。
