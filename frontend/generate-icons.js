const sharp = require('sharp');
const fs = require('fs');
const path = require('path');

// DigitalOcean-themed icon SVG - water droplet with gradient
const createIconSVG = (size) => `
<svg width="${size}" height="${size}" viewBox="0 0 512 512" xmlns="http://www.w3.org/2000/svg">
  <defs>
    <linearGradient id="bgGrad" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" style="stop-color:#0a1628"/>
      <stop offset="100%" style="stop-color:#0d1f3c"/>
    </linearGradient>
    <linearGradient id="dropGrad" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" style="stop-color:#0080FF"/>
      <stop offset="100%" style="stop-color:#00D4FF"/>
    </linearGradient>
    <linearGradient id="innerGrad" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" style="stop-color:#00D4FF"/>
      <stop offset="100%" style="stop-color:#0080FF"/>
    </linearGradient>
  </defs>
  
  <!-- Rounded square background -->
  <rect x="16" y="16" width="480" height="480" rx="96" ry="96" fill="url(#bgGrad)"/>
  
  <!-- Outer glow -->
  <ellipse cx="256" cy="280" rx="140" ry="160" fill="url(#dropGrad)" opacity="0.15"/>
  
  <!-- Main droplet shape -->
  <path d="M256 96 
           C256 96 160 200 160 300 
           C160 380 200 416 256 416 
           C312 416 352 380 352 300 
           C352 200 256 96 256 96Z" 
        fill="url(#dropGrad)"/>
  
  <!-- Inner highlight droplet -->
  <path d="M256 160 
           C256 160 200 230 200 290 
           C200 340 224 360 256 360 
           C288 360 312 340 312 290 
           C312 230 256 160 256 160Z" 
        fill="url(#innerGrad)" opacity="0.6"/>
  
  <!-- Shine highlight -->
  <ellipse cx="220" cy="260" rx="24" ry="32" fill="white" opacity="0.3"/>
  
  <!-- Small bubble -->
  <circle cx="300" cy="340" r="16" fill="white" opacity="0.2"/>
</svg>
`;

const iconsDir = path.join(__dirname, 'src-tauri', 'icons');

const sizes = [
  { name: '32x32.png', size: 32 },
  { name: '128x128.png', size: 128 },
  { name: '128x128@2x.png', size: 256 },
  { name: 'icon.png', size: 512 },
  { name: 'Square30x30Logo.png', size: 30 },
  { name: 'Square44x44Logo.png', size: 44 },
  { name: 'Square71x71Logo.png', size: 71 },
  { name: 'Square89x89Logo.png', size: 89 },
  { name: 'Square107x107Logo.png', size: 107 },
  { name: 'Square142x142Logo.png', size: 142 },
  { name: 'Square150x150Logo.png', size: 150 },
  { name: 'Square284x284Logo.png', size: 284 },
  { name: 'Square310x310Logo.png', size: 310 },
  { name: 'StoreLogo.png', size: 50 },
];

async function generateIcons() {
  console.log('Generating DigitalOcean-themed icons...\n');
  
  for (const { name, size } of sizes) {
    const svg = createIconSVG(512);
    const outputPath = path.join(iconsDir, name);
    
    await sharp(Buffer.from(svg))
      .resize(size, size)
      .png()
      .toFile(outputPath);
    
    console.log(`✓ Generated ${name} (${size}x${size})`);
  }
  
  // Generate ICO for Windows
  console.log('\nGenerating icon.ico...');
  const svg512 = createIconSVG(512);
  const png256 = await sharp(Buffer.from(svg512)).resize(256, 256).png().toBuffer();
  
  // For ICO, we'll just copy the 256x256 PNG as a placeholder
  // A proper ICO would need multiple sizes bundled together
  await sharp(png256).toFile(path.join(iconsDir, 'icon.ico.png'));
  console.log('✓ Generated icon.ico placeholder (use icon.png for ICO conversion)');
  
  // Generate ICNS for macOS (placeholder - needs iconutil)
  console.log('\nNote: For macOS icon.icns, use: iconutil -c icns iconset_folder');
  console.log('      or copy icon.png as a placeholder.\n');
  
  // Copy main icon as icns placeholder
  const mainIcon = await sharp(Buffer.from(createIconSVG(512))).resize(512, 512).png().toBuffer();
  fs.writeFileSync(path.join(iconsDir, 'icon_new.png'), mainIcon);
  
  console.log('✅ All PNG icons generated successfully!');
  console.log('\nTo complete macOS/Windows icons:');
  console.log('  - macOS: Use iconutil or an online converter for icon.icns');
  console.log('  - Windows: Use an online PNG to ICO converter for icon.ico');
}

generateIcons().catch(console.error);

