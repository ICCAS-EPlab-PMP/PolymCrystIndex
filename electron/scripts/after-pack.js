const fs = require('fs')
const path = require('path')

function normalizeWindowsVersion(version) {
  const segments = String(version)
    .split('.')
    .map((segment) => Number.parseInt(segment, 10))
    .filter((segment) => Number.isFinite(segment) && segment >= 0)
    .slice(0, 4)

  while (segments.length < 4) {
    segments.push(0)
  }

  return segments.join('.')
}

module.exports = async function afterPack(context) {
  if (context.electronPlatformName !== 'win32') {
    return
  }

  const productFilename = context.packager.appInfo.productFilename
  const appVersion = context.packager.appInfo.version
  const appVersionWindows = normalizeWindowsVersion(appVersion)
  const executablePath = path.join(context.appOutDir, `${productFilename}.exe`)
  const iconPath = path.resolve(__dirname, '..', '..', 'icon', 'polymindex.ico')

  if (!fs.existsSync(executablePath)) {
    throw new Error(`Packaged executable not found: ${executablePath}`)
  }

  if (!fs.existsSync(iconPath)) {
    throw new Error(`Windows icon not found: ${iconPath}`)
  }

  const { rcedit } = await import('rcedit')

  await rcedit(executablePath, {
    icon: iconPath,
    'file-version': appVersionWindows,
    'product-version': appVersionWindows,
    'version-string': {
      CompanyName: 'PolymCrystIndex Team',
      FileDescription: 'PolymCrystIndex desktop application',
      FileVersion: appVersion,
      InternalName: productFilename,
      OriginalFilename: `${productFilename}.exe`,
      ProductName: 'PolymCrystIndex',
      ProductVersion: appVersion,
    },
  })

  console.log(`afterPack: updated Windows executable resources for ${executablePath}`)
}
