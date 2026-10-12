
package com.garminmatrix
import android.os.Bundle
import android.webkit.JavascriptInterface
import android.webkit.WebView
import androidx.appcompat.app.AppCompatActivity
import com.chaquo.python.Python
import com.chaquo.python.android.AndroidPlatform
import java.io.File
class MainActivity : AppCompatActivity() {
    lateinit var webView: WebView
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        webView = WebView(this); setContentView(webView)
        webView.settings.javaScriptEnabled = true
        webView.settings.domStorageEnabled = true
        webView.settings.allowFileAccess = true
        webView.settings.allowUniversalAccessFromFileURLs = true
        webView.addJavascriptInterface(AndroidBridge(), "Android")
        if (!Python.isStarted()) Python.start(AndroidPlatform(this))
        webView.loadUrl("file:///android_asset/index.html")
    }
    inner class AndroidBridge {
        @JavascriptInterface fun getDatabaseJson(): String {
            val f = File(filesDir, "database.json")
            return if(f.exists()) f.readText() else assets.open("database.json").bufferedReader().readText()
        }
        @JavascriptInterface fun aggiornaDati(email:String, pass:String): String {
            Thread {
                try {
                    val py = Python.getInstance()
                    py.getModule("estrattore_android").callAttr("main_android", filesDir.absolutePath, email, pass)
                    runOnUiThread { webView.reload() }
                } catch(e:Exception){ e.printStackTrace() }
            }.start()
            return "Avviato"
        }
    }
}
