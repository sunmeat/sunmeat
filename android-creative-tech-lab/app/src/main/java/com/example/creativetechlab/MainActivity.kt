package com.example.creativetechlab

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.compose.ui.viewinterop.AndroidView
import coil3.compose.AsyncImage
import coil3.request.ImageRequest
import coil3.request.crossfade
import com.airbnb.lottie.compose.*
import com.masoudss.lib.WaveformSeekBar
import com.patrykandpatrick.vico.compose.cartesian.CartesianChartHost
import com.patrykandpatrick.vico.compose.cartesian.axis.HorizontalAxis
import com.patrykandpatrick.vico.compose.cartesian.axis.VerticalAxis
import com.patrykandpatrick.vico.compose.cartesian.data.CartesianChartModelProducer
import com.patrykandpatrick.vico.compose.cartesian.data.lineModel
import com.patrykandpatrick.vico.compose.cartesian.layer.rememberLineCartesianLayer
import com.patrykandpatrick.vico.compose.cartesian.rememberCartesianChart
import io.github.sceneview.SceneView
import kotlin.math.abs
import kotlin.math.sin

private val Ink = Color(0xFF09111F)
private val Panel = Color(0xFF142237)
private val Cyan = Color(0xFF6EE7F7)
private val Muted = Color(0xFFA7B7CF)
private val Purple = Color(0xFFAB92FF)

class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContent { CreativeTechLab() }
    }
}

@Composable
private fun CreativeTechLab() {
    var selected by rememberSaveable { mutableIntStateOf(0) }
    val names = listOf("Огляд", "3D", "Аудіо", "Дані")
    val symbols = listOf("✦", "◈", "♫", "▥")
    MaterialTheme(
        colorScheme = darkColorScheme(
            primary = Cyan,
            secondary = Purple,
            background = Ink,
            surface = Panel,
            onSurface = Color.White
        )
    ) {
        Scaffold(
            containerColor = Ink,
            bottomBar = {
                NavigationBar(containerColor = Panel) {
                    names.forEachIndexed { index, label ->
                        NavigationBarItem(
                            selected = selected == index,
                            onClick = { selected = index },
                            icon = { Text(symbols[index], fontSize = 21.sp) },
                            label = { Text(label) },
                            alwaysShowLabel = true
                        )
                    }
                }
            }
        ) { innerPadding ->
            Column(
                Modifier.fillMaxSize()
                    .padding(innerPadding)
                    .verticalScroll(rememberScrollState())
                    .padding(horizontal = 20.dp, vertical = 18.dp),
                verticalArrangement = Arrangement.spacedBy(18.dp)
            ) {
                Text("CREATIVE  /  TECH LAB", color = Cyan, fontSize = 12.sp, fontWeight = FontWeight.Bold)
                Text(
                    when (selected) {
                        0 -> "Мультимедіа без меж"
                        1 -> "Торкнися 3D"
                        2 -> "Звук у деталях"
                        else -> "Дані оживають"
                    },
                    fontSize = 29.sp,
                    lineHeight = 35.sp,
                    fontWeight = FontWeight.Bold
                )
                Text(
                    when (selected) {
                        0 -> "П'ять open-source бібліотек. Один Android-додаток."
                        1 -> "SceneView · Filament · орбітальна камера"
                        2 -> "WaveformSeekBar · інтерактивні семпли"
                        else -> "Vico · анімовані графіки Compose"
                    },
                    color = Muted, fontSize = 14.sp
                )
                when (selected) {
                    0 -> OverviewScreen()
                    1 -> ThreeDScreen()
                    2 -> AudioScreen()
                    else -> DataScreen()
                }
                Spacer(Modifier.height(14.dp))
            }
        }
    }
}

@Composable
private fun ShowcaseCard(
    title: String,
    caption: String,
    content: @Composable ColumnScope.() -> Unit
) {
    Card(
        shape = RoundedCornerShape(24.dp),
        colors = CardDefaults.cardColors(containerColor = Panel),
        modifier = Modifier.fillMaxWidth()
    ) {
        Column(
            Modifier.fillMaxWidth().padding(18.dp),
            verticalArrangement = Arrangement.spacedBy(12.dp),
            content = {
                Text(title, fontSize = 19.sp, fontWeight = FontWeight.SemiBold)
                Text(caption, color = Muted, fontSize = 13.sp)
                content()
            }
        )
    }
}

@Composable
private fun OverviewScreen() {
    ShowcaseCard(
        "01 / Coil 3",
        "Завантаження фотографії з мережі та кешування"
    ) {
        AsyncImage(
            model = ImageRequest.Builder(LocalContext.current)
                .data("https://images.unsplash.com/photo-1493225457124-a3eb161ffa5f?w=1000&q=85")
                .crossfade(true)
                .build(),
            contentDescription = "Концертне освітлення",
            contentScale = ContentScale.Crop,
            modifier = Modifier.fillMaxWidth().height(205.dp)
                .clip(RoundedCornerShape(16.dp)).background(Ink)
        )
        Text("Зображення завантажується асинхронно", color = Cyan, fontSize = 12.sp)
    }
    ShowcaseCard("02 / Lottie", "JSON-анімація, незалежна від розміру екрана") {
        var playing by remember { mutableStateOf(true) }
        val composition by rememberLottieComposition(LottieCompositionSpec.RawRes(R.raw.pulse))
        val progress by animateLottieCompositionAsState(
            composition = composition,
            iterations = LottieConstants.IterateForever,
            isPlaying = playing
        )
        Row(verticalAlignment = Alignment.CenterVertically) {
            LottieAnimation(
                composition = composition,
                progress = { progress },
                modifier = Modifier.size(145.dp)
            )
            Column {
                Text("NEON PULSE", color = Cyan, fontSize = 15.sp, fontWeight = FontWeight.Bold)
                Text("60 FPS · векторна анімація", color = Muted, fontSize = 12.sp)
                Spacer(Modifier.height(8.dp))
                Button(onClick = { playing = !playing }) {
                    Text(if (playing) "Пауза" else "Продовжити")
                }
            }
        }
    }
    Text("Усі п'ять бібліотек підключені через Gradle.", color = Muted, fontSize = 12.sp)
}

@Composable
private fun ThreeDScreen() {
    ShowcaseCard("03 / SceneView", "Обертай 3D-сферу жестом. Рендеринг на GPU.") {
        Box(
            modifier = Modifier.fillMaxWidth().height(360.dp)
                .clip(RoundedCornerShape(18.dp)).background(Color(0xFF080E1B))
        ) {
            SceneView(modifier = Modifier.fillMaxSize()) {
                SphereNode(radius = 0.35f)
            }
        }
        Text("Керування: перетягуй, щоб обертати, масштабування двома пальцями.", color = Cyan, fontSize = 13.sp)
    }
}

private fun waveformSamples(seed: Int): IntArray = IntArray(140) { i ->
    (12 + abs(sin((i + seed * 19) * 0.18) * 53) +
        abs(sin((i + seed * 5) * 0.057) * 24)).toInt()
}

@Composable
private fun AudioScreen() {
    var seed by rememberSaveable { mutableIntStateOf(0) }
    var progress by rememberSaveable { mutableFloatStateOf(38f) }
    ShowcaseCard("04 / WaveformSeekBar", "Звукова хвиля з інтерактивною позицією відтворення") {
        AndroidView(
            factory = { context ->
                WaveformSeekBar(context).apply {
                    waveWidth = 4f
                    waveGap = 3f
                    waveMinHeight = 5f
                    waveCornerRadius = 3f
                    waveBackgroundColor = android.graphics.Color.rgb(65, 87, 119)
                    waveProgressColor = android.graphics.Color.rgb(110, 231, 247)
                    maxProgress = 100f
                }
            },
            update = {
                it.setSampleFrom(waveformSamples(seed))
                it.progress = progress
            },
            modifier = Modifier.fillMaxWidth().height(160.dp)
        )
        Text("Позиція: " + progress.toInt() + "%", color = Cyan, fontSize = 14.sp)
        Slider(value = progress, onValueChange = { progress = it }, valueRange = 0f..100f)
        Button(onClick = { seed += 1 }) { Text("Згенерувати іншу хвилю") }
        Text(
            "Демонстрація використовує синтетичні амплітуди. Доступу до мікрофона не потребує.",
            color = Muted, fontSize = 12.sp
        )
    }
}

@Composable
private fun DataScreen() {
    var seed by rememberSaveable { mutableIntStateOf(0) }
    val producer = remember { CartesianChartModelProducer() }
    LaunchedEffect(seed) {
        producer.runTransaction {
            lineModel {
                series(y = List(16) { i ->
                    (7 + 3 * sin(i * 0.67 + seed) + 2 * sin(i * 1.6 - seed)).toDouble()
                })
            }
        }
    }
    ShowcaseCard("05 / Vico Charts", "Анімований лінійний графік із масштабуванням") {
        CartesianChartHost(
            chart = rememberCartesianChart(
                rememberLineCartesianLayer(),
                startAxis = VerticalAxis.rememberStart(),
                bottomAxis = HorizontalAxis.rememberBottom()
            ),
            modelProducer = producer,
            modifier = Modifier.fillMaxWidth().height(310.dp)
        )
        Button(onClick = { seed += 1 }) { Text("Оновити набір даних") }
        Text("Графік змінюється без перезавантаження екрана.", color = Muted, fontSize = 12.sp)
    }
}
