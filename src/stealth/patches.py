"""
Jarvis Web Agent - Stealth Patches
JavaScript patches to evade bot detection
"""

from playwright.async_api import Page
from typing import Dict, Any
from loguru import logger


async def apply_stealth_patches(page: Page, fingerprint: Dict[str, Any]):
    """
    Apply stealth patches to a page before navigation
    
    These patches modify browser APIs to appear more human-like
    and evade common bot detection techniques.
    """
    
    # Core stealth script
    stealth_script = """
    () => {
        // Store original values
        const originalQuery = window.navigator.permissions.query;
        
        // ===========================================
        // 1. Navigator.webdriver
        // ===========================================
        Object.defineProperty(navigator, 'webdriver', {
            get: () => false,
            configurable: true
        });
        
        // Delete webdriver property entirely
        delete navigator.__proto__.webdriver;
        
        // ===========================================
        // 2. Navigator.plugins
        // ===========================================
        const makePluginArray = () => {
            const plugins = [
                { name: 'Chrome PDF Plugin', filename: 'internal-pdf-viewer', description: 'Portable Document Format' },
                { name: 'Chrome PDF Viewer', filename: 'mhjfbmdgcfjbbpaeojofohoefgiehjai', description: '' },
                { name: 'Native Client', filename: 'internal-nacl-plugin', description: '' }
            ];
            
            const pluginArray = Object.create(PluginArray.prototype);
            plugins.forEach((p, i) => {
                const plugin = Object.create(Plugin.prototype);
                Object.defineProperties(plugin, {
                    name: { value: p.name, enumerable: true },
                    filename: { value: p.filename, enumerable: true },
                    description: { value: p.description, enumerable: true },
                    length: { value: 1, enumerable: true }
                });
                pluginArray[i] = plugin;
            });
            
            Object.defineProperty(pluginArray, 'length', { value: plugins.length });
            pluginArray.item = (i) => pluginArray[i] || null;
            pluginArray.namedItem = (name) => 
                Array.from(pluginArray).find(p => p.name === name) || null;
            pluginArray.refresh = () => {};
            
            return pluginArray;
        };
        
        Object.defineProperty(navigator, 'plugins', {
            get: () => makePluginArray(),
            configurable: true
        });
        
        // ===========================================
        // 3. Navigator.languages
        // ===========================================
        Object.defineProperty(navigator, 'languages', {
            get: () => ['en-US', 'en'],
            configurable: true
        });
        
        // ===========================================
        // 4. Permissions API
        // ===========================================
        window.navigator.permissions.query = (parameters) => {
            if (parameters.name === 'notifications') {
                return Promise.resolve({ state: Notification.permission });
            }
            return originalQuery.call(window.navigator.permissions, parameters);
        };
        
        // ===========================================
        // 5. Chrome runtime
        // ===========================================
        window.chrome = {
            runtime: {
                connect: () => {},
                sendMessage: () => {},
                onMessage: { addListener: () => {} }
            },
            loadTimes: () => ({
                commitLoadTime: Date.now() / 1000,
                connectionInfo: 'http/1.1',
                finishDocumentLoadTime: Date.now() / 1000,
                finishLoadTime: Date.now() / 1000,
                firstPaintAfterLoadTime: 0,
                firstPaintTime: Date.now() / 1000,
                navigationType: 'Other',
                npnNegotiatedProtocol: 'http/1.1',
                requestTime: Date.now() / 1000,
                startLoadTime: Date.now() / 1000,
                wasAlternateProtocolAvailable: false,
                wasFetchedViaSpdy: false,
                wasNpnNegotiated: false
            }),
            csi: () => ({
                onloadT: Date.now(),
                pageT: Date.now() - performance.timing.navigationStart,
                startE: Date.now(),
                tran: 15
            }),
            app: {
                isInstalled: false,
                InstallState: { DISABLED: 'disabled', INSTALLED: 'installed', NOT_INSTALLED: 'not_installed' },
                RunningState: { CANNOT_RUN: 'cannot_run', READY_TO_RUN: 'ready_to_run', RUNNING: 'running' }
            }
        };
        
        // ===========================================
        // 6. WebGL Vendor/Renderer
        // ===========================================
        const getParameter = WebGLRenderingContext.prototype.getParameter;
        WebGLRenderingContext.prototype.getParameter = function(parameter) {
            // UNMASKED_VENDOR_WEBGL
            if (parameter === 37445) {
                return 'Intel Inc.';
            }
            // UNMASKED_RENDERER_WEBGL
            if (parameter === 37446) {
                return 'Intel Iris OpenGL Engine';
            }
            return getParameter.call(this, parameter);
        };
        
        // Also patch WebGL2
        if (typeof WebGL2RenderingContext !== 'undefined') {
            const getParameter2 = WebGL2RenderingContext.prototype.getParameter;
            WebGL2RenderingContext.prototype.getParameter = function(parameter) {
                if (parameter === 37445) return 'Intel Inc.';
                if (parameter === 37446) return 'Intel Iris OpenGL Engine';
                return getParameter2.call(this, parameter);
            };
        }
        
        // ===========================================
        // 7. Notification API
        // ===========================================
        if (!window.Notification) {
            window.Notification = {
                permission: 'default',
                requestPermission: () => Promise.resolve('default')
            };
        }
        
        // ===========================================
        // 8. Connection (navigator.connection)
        // ===========================================
        Object.defineProperty(navigator, 'connection', {
            get: () => ({
                effectiveType: '4g',
                rtt: 100,
                downlink: 10,
                saveData: false
            }),
            configurable: true
        });
        
        // ===========================================
        // 9. Hardware Concurrency
        // ===========================================
        Object.defineProperty(navigator, 'hardwareConcurrency', {
            get: () => HARDWARE_CONCURRENCY_VALUE,
            configurable: true
        });
        
        // ===========================================
        // 10. Device Memory
        // ===========================================
        Object.defineProperty(navigator, 'deviceMemory', {
            get: () => DEVICE_MEMORY_VALUE,
            configurable: true
        });
        
        // ===========================================
        // 11. Console.debug detection
        // ===========================================
        const originalDebug = console.debug;
        console.debug = function(...args) {
            // Filter out automation detection logs
            const str = args.join(' ');
            if (str.includes('automation') || str.includes('webdriver')) {
                return;
            }
            return originalDebug.apply(console, args);
        };
        
        // ===========================================
        // 12. Iframe contentWindow
        // ===========================================
        const originalContentWindow = Object.getOwnPropertyDescriptor(
            HTMLIFrameElement.prototype, 'contentWindow'
        );
        Object.defineProperty(HTMLIFrameElement.prototype, 'contentWindow', {
            get: function() {
                const iframe = originalContentWindow.get.call(this);
                if (iframe) {
                    try {
                        // Re-apply some patches to iframes
                        Object.defineProperty(iframe.navigator, 'webdriver', {
                            get: () => false
                        });
                    } catch (e) {}
                }
                return iframe;
            }
        });
    }
    """
    
    # Inject fingerprint values
    hardware_concurrency = fingerprint.get("hardware_concurrency", 8)
    device_memory = fingerprint.get("device_memory", 8)
    
    stealth_script = stealth_script.replace(
        "HARDWARE_CONCURRENCY_VALUE",
        str(hardware_concurrency)
    ).replace(
        "DEVICE_MEMORY_VALUE",
        str(device_memory)
    )
    
    # Add script to run on every navigation
    await page.add_init_script(stealth_script)
    
    logger.debug("Stealth patches applied")


async def apply_canvas_noise(page: Page, seed: str):
    """
    Apply canvas fingerprint noise
    
    This modifies canvas operations to produce a unique but consistent
    fingerprint based on the identity seed.
    """
    
    canvas_script = f"""
    () => {{
        const seed = '{seed}';
        
        // Simple hash function
        const hash = (str) => {{
            let h = 0;
            for (let i = 0; i < str.length; i++) {{
                h = ((h << 5) - h) + str.charCodeAt(i);
                h = h & h;
            }}
            return h;
        }};
        
        const noise = hash(seed) / 2147483647;
        
        // Patch toDataURL
        const originalToDataURL = HTMLCanvasElement.prototype.toDataURL;
        HTMLCanvasElement.prototype.toDataURL = function(...args) {{
            const ctx = this.getContext('2d');
            if (ctx) {{
                const imageData = ctx.getImageData(0, 0, this.width, this.height);
                for (let i = 0; i < imageData.data.length; i += 4) {{
                    // Add slight noise to RGB channels
                    imageData.data[i] = imageData.data[i] + Math.floor(noise * 2);
                }}
                ctx.putImageData(imageData, 0, 0);
            }}
            return originalToDataURL.apply(this, args);
        }};
    }}
    """
    
    await page.add_init_script(canvas_script)
