import type { ExtensionContext } from "vscode";

import { LanguageClient } from "vscode-languageclient/lib/node/main";

export async function activate(context: ExtensionContext) {
  const executable = {
    command: "bun",
    args: ["run", "mylang-lsp", "--stdio"],
  };

  const serverOptions = {
    run: executable,
    debug: executable,
  };

  const clientOptions = {
    documentSelector: [
      {
        scheme: "file",
        language: "plaintext",
      },
    ],
  };

  const client = new LanguageClient(
    "blacklist-extension-id",
    "Blacklister",
    serverOptions,
    clientOptions
  );

  await client.start();

  context.subscriptions.push({
    dispose: () => client.stop(),
  });
}
