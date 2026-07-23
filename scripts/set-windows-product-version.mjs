import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import * as ResEdit from "resedit";

const projectRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");

function displayVersion(version) {
  const calendar = version.match(/^(\d+\.\d+\.\d+)-(\d+)\.(\d+)$/);
  return calendar ? `${calendar[1]}.${calendar[2]}-${calendar[3]}` : version;
}

if (process.platform === "win32") {
  const config = JSON.parse(
    fs.readFileSync(path.join(projectRoot, "src-tauri", "tauri.conf.json"), "utf8"),
  );
  const targetDirectory = process.env.CARGO_TARGET_DIR
    ? path.resolve(projectRoot, process.env.CARGO_TARGET_DIR)
    : path.join(projectRoot, "target");
  const explicitPath = process.argv[2] ? path.resolve(projectRoot, process.argv[2]) : null;
  const targetTriple = process.env.TAURI_ENV_TARGET_TRIPLE;
  const candidates = [
    explicitPath,
    targetTriple
      ? path.join(targetDirectory, targetTriple, "release", "sbt-desk-tool.exe")
      : null,
    path.join(targetDirectory, "release", "sbt-desk-tool.exe"),
  ].filter(Boolean);
  const executable = candidates.find((candidate) => fs.existsSync(candidate));

  if (!executable) {
    throw new Error(`Unable to find Windows executable. Checked: ${candidates.join(", ")}`);
  }

  const visibleVersion = displayVersion(config.version);
  const fileVersion = visibleVersion.replace(/-\d+$/, "");
  const binary = fs.readFileSync(executable);
  const image = ResEdit.NtExecutable.from(binary);
  const resources = ResEdit.NtExecutableResource.from(image);
  const versionInfos = ResEdit.Resource.VersionInfo.fromEntries(resources.entries);
  if (versionInfos.length === 0) {
    throw new Error(`Windows version resource is missing: ${executable}`);
  }

  for (const versionInfo of versionInfos) {
    const languages = versionInfo.getAllLanguagesForStringValues();
    for (const language of languages) {
      // VS_FIXEDFILEINFO only supports four u16 numbers. Keep the build suffix
      // in ProductVersion while FileVersion represents the four-part release.
      versionInfo.setFileVersion(fileVersion, language.lang);
      versionInfo.setProductVersion(fileVersion, language.lang);
      versionInfo.setStringValues(language, {
        FileVersion: fileVersion,
        ProductVersion: visibleVersion,
      });
    }
    versionInfo.outputToResourceEntries(resources.entries);
  }

  resources.outputResource(image);
  const temporary = `${executable}.version.tmp`;
  fs.writeFileSync(temporary, Buffer.from(image.generate()));
  try {
    fs.copyFileSync(temporary, executable);
  } finally {
    fs.rmSync(temporary, { force: true });
  }
  console.log(`Windows FileVersion set to ${fileVersion}; ProductVersion set to ${visibleVersion}`);
}
