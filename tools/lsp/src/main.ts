import {
  createConnection,
  TextDocuments,
  ProposedFeatures,
} from "vscode-languageserver/node.js";

import { TextDocument } from "vscode-languageserver-textdocument";

const connection = createConnection(ProposedFeatures.all);
const documents: TextDocuments<TextDocument> = new TextDocuments(TextDocument);

documents.listen(connection);
connection.listen();
