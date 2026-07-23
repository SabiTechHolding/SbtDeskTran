const repository = process.env.GITHUB_REPOSITORY;
const tag = process.env.RELEASE_TAG;
const token = process.env.GH_TOKEN;

if (!repository || !tag) {
  throw new Error("GITHUB_REPOSITORY and RELEASE_TAG are required");
}

const headers = {
  Accept: "application/vnd.github+json",
  "User-Agent": "SbtDeskTool-release-validator",
  "X-GitHub-Api-Version": "2022-11-28",
};
if (token) headers.Authorization = `Bearer ${token}`;

async function githubJson(url) {
  const response = await fetch(url, { headers });
  if (!response.ok) {
    throw new Error(`${response.status} ${response.statusText}: ${url}`);
  }
  return response.json();
}

async function githubAsset(asset) {
  const response = await fetch(asset.url, {
    headers: { ...headers, Accept: "application/octet-stream" },
  });
  if (!response.ok) {
    throw new Error(`${response.status} ${response.statusText}: ${asset.name}`);
  }
  return Buffer.from(await response.arrayBuffer());
}

const release = await githubJson(
  `https://api.github.com/repos/${repository}/releases/tags/${encodeURIComponent(tag)}`,
);
const assetsById = new Map(release.assets.map((asset) => [String(asset.id), asset]));
const assetsByName = new Map(release.assets.map((asset) => [asset.name, asset]));
const manifestAsset = assetsByName.get("latest.json");
if (!manifestAsset) throw new Error("Release does not contain latest.json");

const manifest = JSON.parse((await githubAsset(manifestAsset)).toString("utf8"));
if (!manifest.version || !manifest.platforms) {
  throw new Error("latest.json is missing version or platforms");
}

for (const [platform, update] of Object.entries(manifest.platforms)) {
  const assetId = String(update.url ?? "").match(/\/releases\/assets\/(\d+)(?:$|[?#])/)?.[1];
  if (!assetId) {
    throw new Error(`${platform}: updater URL is not a GitHub release asset URL`);
  }

  const packageAsset = assetsById.get(assetId);
  if (!packageAsset) {
    throw new Error(`${platform}: updater references missing asset id ${assetId}`);
  }

  const signatureAsset = assetsByName.get(`${packageAsset.name}.sig`);
  if (!signatureAsset) {
    throw new Error(`${platform}: missing ${packageAsset.name}.sig`);
  }

  const signature = (await githubAsset(signatureAsset)).toString("utf8").trim();
  if (signature !== update.signature) {
    throw new Error(`${platform}: latest.json signature does not match ${signatureAsset.name}`);
  }
}

console.log(
  `Validated ${Object.keys(manifest.platforms).length} updater targets for ${tag} (${manifest.version}).`,
);
