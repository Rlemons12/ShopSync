package com.shopsync.tablet.ui.screen.scanner

import android.Manifest
import android.content.pm.PackageManager
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import androidx.camera.core.CameraSelector
import androidx.camera.core.ImageAnalysis
import androidx.camera.core.Preview
import androidx.camera.lifecycle.ProcessCameraProvider
import androidx.camera.view.PreviewView
import androidx.compose.foundation.Canvas
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.BoxWithConstraints
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.aspectRatio
import androidx.compose.foundation.layout.fillMaxHeight
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.AssistChip
import androidx.compose.material3.Button
import androidx.compose.material3.Card
import androidx.compose.material3.ElevatedCard
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.DisposableEffect
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.geometry.CornerRadius
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.geometry.Rect
import androidx.compose.ui.geometry.Size
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.StrokeCap
import androidx.compose.ui.graphics.drawscope.Stroke
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.platform.LocalLifecycleOwner
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.viewinterop.AndroidView
import androidx.core.content.ContextCompat
import androidx.lifecycle.ViewModel
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import androidx.lifecycle.viewModelScope
import androidx.lifecycle.viewmodel.compose.viewModel
import com.google.common.util.concurrent.ListenableFuture
import com.google.mlkit.vision.barcode.BarcodeScannerOptions
import com.google.mlkit.vision.barcode.BarcodeScanning
import com.google.mlkit.vision.barcode.common.Barcode
import com.google.mlkit.vision.common.InputImage
import com.shopsync.tablet.data.repository.ScannerRepository
import com.shopsync.tablet.domain.model.ScanLog
import com.shopsync.tablet.ui.components.MessagePane
import com.shopsync.tablet.ui.components.formatTimestamp
import com.shopsync.tablet.ui.simpleViewModelFactory
import java.util.concurrent.ExecutorService
import java.util.concurrent.Executors
import kotlin.math.max
import kotlinx.coroutines.flow.SharingStarted
import kotlinx.coroutines.flow.map
import kotlinx.coroutines.flow.stateIn
import kotlinx.coroutines.launch

enum class ScanMode {
    SetMaster,
    Verify
}

data class ScannerUiState(
    val masterCode: String? = null,
    val mode: ScanMode = ScanMode.SetMaster,
    val status: String = "Point the camera at the master barcode to arm verification.",
    val lastReadValue: String? = null
)

private data class OverlayBarcode(
    val rawValue: String,
    val left: Float,
    val top: Float,
    val right: Float,
    val bottom: Float
)

class ScannerViewModel(
    private val repository: ScannerRepository
) : ViewModel() {
    private val state = kotlinx.coroutines.flow.MutableStateFlow(ScannerUiState())
    val uiState = state.stateIn(viewModelScope, SharingStarted.WhileSubscribed(5_000), ScannerUiState())
    val logs = repository.observeRecentScans().map { it }.stateIn(viewModelScope, SharingStarted.WhileSubscribed(5_000), emptyList())

    fun armMasterCapture() {
        state.value = state.value.copy(
            mode = ScanMode.SetMaster,
            status = "Point the camera at the barcode you want to save as master."
        )
    }

    fun clearMaster() {
        state.value = ScannerUiState(status = "Master cleared. Scan a new master barcode.")
    }

    fun processScannedValue(rawValue: String) {
        val trimmed = rawValue.trim()
        if (trimmed.isBlank()) return

        val current = state.value
        if (current.lastReadValue == trimmed) return

        if (current.mode == ScanMode.SetMaster || current.masterCode.isNullOrBlank()) {
            state.value = current.copy(
                masterCode = trimmed,
                mode = ScanMode.Verify,
                status = "Master set. Scan another code to verify against it.",
                lastReadValue = trimmed
            )
            return
        }

        val matched = trimmed == current.masterCode
        val score = if (matched) 100 else 0
        viewModelScope.launch {
            repository.saveScan(current.masterCode, trimmed, matched, score)
            state.value = state.value.copy(
                mode = ScanMode.Verify,
                status = if (matched) "PASS: barcode matches the master." else "FAIL: barcode does not match the master.",
                lastReadValue = trimmed
            )
        }
    }

    fun acceptManualEntry(value: String) {
        processScannedValue(value)
    }
}

@Composable
fun ScannerRoute(repository: ScannerRepository) {
    val viewModel: ScannerViewModel = viewModel(factory = simpleViewModelFactory { ScannerViewModel(repository) })
    ScannerScreen(viewModel)
}

@Composable
private fun ScannerScreen(viewModel: ScannerViewModel) {
    val uiState by viewModel.uiState.collectAsStateWithLifecycle()
    val logs by viewModel.logs.collectAsStateWithLifecycle()
    val context = LocalContext.current
    var cameraPermissionGranted by rememberSaveable {
        mutableStateOf(
            ContextCompat.checkSelfPermission(context, Manifest.permission.CAMERA) == PackageManager.PERMISSION_GRANTED
        )
    }
    val permissionLauncher = rememberLauncherForActivityResult(ActivityResultContracts.RequestPermission()) { granted ->
        cameraPermissionGranted = granted
    }
    var manualEntry by rememberSaveable { mutableStateOf("") }

    LaunchedEffect(Unit) {
        if (!cameraPermissionGranted) {
            permissionLauncher.launch(Manifest.permission.CAMERA)
        }
    }

    BoxWithConstraints(modifier = Modifier.fillMaxSize().padding(24.dp)) {
        val wide = maxWidth >= 900.dp
        if (wide) {
            Row(horizontalArrangement = Arrangement.spacedBy(20.dp), modifier = Modifier.fillMaxSize()) {
                ScannerCapturePane(
                    uiState = uiState,
                    cameraPermissionGranted = cameraPermissionGranted,
                    onRequestPermission = { permissionLauncher.launch(Manifest.permission.CAMERA) },
                    onBarcodeDetected = viewModel::processScannedValue,
                    manualEntry = manualEntry,
                    onManualEntryChanged = { manualEntry = it },
                    onSubmitManualEntry = {
                        viewModel.acceptManualEntry(manualEntry)
                        manualEntry = ""
                    },
                    onArmMaster = viewModel::armMasterCapture,
                    onClearMaster = viewModel::clearMaster,
                    modifier = Modifier.weight(1f).fillMaxHeight()
                )
                ScannerHistoryPane(logs = logs, modifier = Modifier.weight(0.9f).fillMaxHeight())
            }
        } else {
            Column(verticalArrangement = Arrangement.spacedBy(20.dp), modifier = Modifier.fillMaxSize()) {
                ScannerCapturePane(
                    uiState = uiState,
                    cameraPermissionGranted = cameraPermissionGranted,
                    onRequestPermission = { permissionLauncher.launch(Manifest.permission.CAMERA) },
                    onBarcodeDetected = viewModel::processScannedValue,
                    manualEntry = manualEntry,
                    onManualEntryChanged = { manualEntry = it },
                    onSubmitManualEntry = {
                        viewModel.acceptManualEntry(manualEntry)
                        manualEntry = ""
                    },
                    onArmMaster = viewModel::armMasterCapture,
                    onClearMaster = viewModel::clearMaster,
                    modifier = Modifier.weight(1f).fillMaxWidth()
                )
                ScannerHistoryPane(logs = logs, modifier = Modifier.weight(1f).fillMaxWidth())
            }
        }
    }
}

@Composable
private fun ScannerCapturePane(
    uiState: ScannerUiState,
    cameraPermissionGranted: Boolean,
    onRequestPermission: () -> Unit,
    onBarcodeDetected: (String) -> Unit,
    manualEntry: String,
    onManualEntryChanged: (String) -> Unit,
    onSubmitManualEntry: () -> Unit,
    onArmMaster: () -> Unit,
    onClearMaster: () -> Unit,
    modifier: Modifier
) {
    var overlayBarcodes by remember { mutableStateOf(emptyList<OverlayBarcode>()) }

    ElevatedCard(modifier = modifier) {
        Column(
            modifier = Modifier.fillMaxSize().padding(20.dp),
            verticalArrangement = Arrangement.spacedBy(16.dp)
        ) {
            Text("Live barcode scanner", style = MaterialTheme.typography.headlineSmall)
            Text(
                "CameraX streams frames into ML Kit barcode scanning and applies the original ShopSync master/verify workflow on-device.",
                color = MaterialTheme.colorScheme.onSurfaceVariant
            )
            if (cameraPermissionGranted) {
                Box(
                    modifier = Modifier
                        .fillMaxWidth()
                        .weight(1f, fill = false)
                        .border(1.dp, MaterialTheme.colorScheme.outline.copy(alpha = 0.35f), RoundedCornerShape(24.dp))
                        .background(MaterialTheme.colorScheme.surfaceVariant.copy(alpha = 0.4f), RoundedCornerShape(24.dp))
                        .padding(12.dp)
                ) {
                    BarcodeCameraPreview(
                        onBarcodeDetected = onBarcodeDetected,
                        onOverlayChanged = { overlayBarcodes = it },
                        modifier = Modifier
                            .fillMaxWidth()
                            .aspectRatio(16f / 9f)
                    )
                    ScannerOverlay(
                        modifier = Modifier
                            .matchParentSize()
                            .padding(6.dp),
                        barcodes = overlayBarcodes,
                        mode = uiState.mode,
                        status = uiState.status,
                        lastReadValue = uiState.lastReadValue
                    )
                }
            } else {
                MessagePane(
                    title = "Camera permission required",
                    message = "Grant camera access to scan barcodes directly from the tablet camera.",
                    modifier = Modifier
                        .fillMaxWidth()
                        .weight(1f, fill = false)
                )
                Button(onClick = onRequestPermission) {
                    Text("Grant camera access")
                }
            }
            Text("Mode: ${if (uiState.mode == ScanMode.SetMaster) "Capture master" else "Verify"}")
            Text("Master: ${uiState.masterCode ?: "(none)"}", color = MaterialTheme.colorScheme.primary)
            Text(uiState.status)
            if (overlayBarcodes.isNotEmpty()) {
                AssistChip(
                    onClick = {},
                    label = {
                        Text(
                            "Detected ${overlayBarcodes.first().rawValue.take(32)}",
                            maxLines = 1
                        )
                    }
                )
            }
            Row(horizontalArrangement = Arrangement.spacedBy(12.dp)) {
                Button(onClick = onArmMaster) { Text("Scan new master") }
                TextButton(onClick = onClearMaster) { Text("Clear master") }
            }
            OutlinedTextField(
                value = manualEntry,
                onValueChange = onManualEntryChanged,
                modifier = Modifier.fillMaxWidth(),
                label = { Text("Fallback manual entry") },
                supportingText = { Text("Use this if the barcode is damaged or the camera cannot read it.") }
            )
            Button(onClick = onSubmitManualEntry, enabled = manualEntry.isNotBlank()) {
                Text("Submit manual entry")
            }
        }
    }
}

@Composable
private fun BarcodeCameraPreview(
    onBarcodeDetected: (String) -> Unit,
    onOverlayChanged: (List<OverlayBarcode>) -> Unit,
    modifier: Modifier = Modifier
) {
    val context = LocalContext.current
    val lifecycleOwner = LocalLifecycleOwner.current
    val mainExecutor = remember(context) { ContextCompat.getMainExecutor(context) }
    val previewView = remember {
        PreviewView(context).apply {
            implementationMode = PreviewView.ImplementationMode.COMPATIBLE
            scaleType = PreviewView.ScaleType.FIT_CENTER
        }
    }
    val cameraProviderFuture = remember { ProcessCameraProvider.getInstance(context) }
    val analysisExecutor = remember { Executors.newSingleThreadExecutor() }

    DisposableEffect(lifecycleOwner, previewView) {
        val scanner = BarcodeScanning.getClient(
            BarcodeScannerOptions.Builder()
                .setBarcodeFormats(
                    Barcode.FORMAT_QR_CODE,
                    Barcode.FORMAT_AZTEC,
                    Barcode.FORMAT_CODE_128,
                    Barcode.FORMAT_CODE_39,
                    Barcode.FORMAT_DATA_MATRIX,
                    Barcode.FORMAT_EAN_13,
                    Barcode.FORMAT_EAN_8,
                    Barcode.FORMAT_PDF417,
                    Barcode.FORMAT_UPC_A,
                    Barcode.FORMAT_UPC_E
                )
                .build()
        )

        val listener = Runnable {
            val cameraProvider = cameraProviderFuture.get()
            val preview = Preview.Builder().build().also {
                it.surfaceProvider = previewView.surfaceProvider
            }
            val analysis = ImageAnalysis.Builder()
                .setBackpressureStrategy(ImageAnalysis.STRATEGY_KEEP_ONLY_LATEST)
                .build()

            analysis.setAnalyzer(analysisExecutor) { imageProxy ->
                val mediaImage = imageProxy.image
                if (mediaImage == null) {
                    imageProxy.close()
                    return@setAnalyzer
                }
                val image = InputImage.fromMediaImage(mediaImage, imageProxy.imageInfo.rotationDegrees)
                scanner.process(image)
                    .addOnSuccessListener { barcodes ->
                        val overlays = barcodes.mapNotNull { barcode ->
                            barcode.boundingBox?.let { bounds ->
                                mapToOverlayBarcode(
                                    rawValue = barcode.rawValue ?: return@let null,
                                    left = bounds.left.toFloat(),
                                    top = bounds.top.toFloat(),
                                    right = bounds.right.toFloat(),
                                    bottom = bounds.bottom.toFloat(),
                                    sourceWidth = imageProxy.width.toFloat(),
                                    sourceHeight = imageProxy.height.toFloat(),
                                    rotationDegrees = imageProxy.imageInfo.rotationDegrees
                                )
                            }
                        }
                        mainExecutor.execute {
                            onOverlayChanged(overlays)
                        }
                        barcodes.firstOrNull()?.rawValue?.let(onBarcodeDetected)
                    }
                    .addOnFailureListener {
                        mainExecutor.execute { onOverlayChanged(emptyList()) }
                    }
                    .addOnCompleteListener {
                        imageProxy.close()
                    }
            }

            cameraProvider.unbindAll()
            cameraProvider.bindToLifecycle(
                lifecycleOwner,
                CameraSelector.DEFAULT_BACK_CAMERA,
                preview,
                analysis
            )
        }

        cameraProviderFuture.addListener(listener, ContextCompat.getMainExecutor(context))

        onDispose {
            runCatching { cameraProviderFuture.get().unbindAll() }
            onOverlayChanged(emptyList())
            scanner.close()
            analysisExecutor.shutdown()
        }
    }

    AndroidView(
        factory = { previewView },
        modifier = modifier
            .fillMaxWidth()
            .size(width = 640.dp, height = 360.dp)
            .background(MaterialTheme.colorScheme.surfaceVariant)
    )
}

@Composable
private fun ScannerOverlay(
    barcodes: List<OverlayBarcode>,
    mode: ScanMode,
    status: String,
    lastReadValue: String?,
    modifier: Modifier = Modifier
) {
    val targetColor = if (mode == ScanMode.SetMaster) Color(0xFFFFA24B) else Color(0xFF49D7B9)
    val boxColor = if (status.startsWith("FAIL")) Color(0xFFFF6B6B) else targetColor

    Box(modifier = modifier) {
        Canvas(modifier = Modifier.matchParentSize()) {
            val guideWidth = size.width * 0.78f
            val guideHeight = size.height * 0.34f
            val guideLeft = (size.width - guideWidth) / 2f
            val guideTop = (size.height - guideHeight) / 2f
            val guideRect = Rect(guideLeft, guideTop, guideLeft + guideWidth, guideTop + guideHeight)
            val corner = size.minDimension * 0.03f

            drawRoundRect(
                color = Color.Black.copy(alpha = 0.22f),
                topLeft = Offset.Zero,
                size = size
            )
            drawRoundRect(
                color = Color.Transparent,
                topLeft = guideRect.topLeft,
                size = guideRect.size,
                cornerRadius = CornerRadius(28f, 28f),
                blendMode = androidx.compose.ui.graphics.BlendMode.Clear
            )
            drawRoundRect(
                color = targetColor,
                topLeft = guideRect.topLeft,
                size = guideRect.size,
                cornerRadius = CornerRadius(28f, 28f),
                style = Stroke(width = 6f)
            )

            val corners = listOf(
                Offset(guideRect.left, guideRect.top) to listOf(
                    Offset(guideRect.left + corner, guideRect.top),
                    Offset(guideRect.left, guideRect.top + corner)
                ),
                Offset(guideRect.right, guideRect.top) to listOf(
                    Offset(guideRect.right - corner, guideRect.top),
                    Offset(guideRect.right, guideRect.top + corner)
                ),
                Offset(guideRect.left, guideRect.bottom) to listOf(
                    Offset(guideRect.left + corner, guideRect.bottom),
                    Offset(guideRect.left, guideRect.bottom - corner)
                ),
                Offset(guideRect.right, guideRect.bottom) to listOf(
                    Offset(guideRect.right - corner, guideRect.bottom),
                    Offset(guideRect.right, guideRect.bottom - corner)
                )
            )
            corners.forEach { (start, ends) ->
                ends.forEach { end ->
                    drawLine(color = targetColor, start = start, end = end, strokeWidth = 9f, cap = StrokeCap.Round)
                }
            }

            barcodes.take(4).forEach { barcode ->
                val left = barcode.left * size.width
                val top = barcode.top * size.height
                val width = max((barcode.right - barcode.left) * size.width, 8f)
                val height = max((barcode.bottom - barcode.top) * size.height, 8f)
                drawRoundRect(
                    color = boxColor,
                    topLeft = Offset(left, top),
                    size = Size(width, height),
                    cornerRadius = CornerRadius(16f, 16f),
                    style = Stroke(width = 5f)
                )
            }
        }

        Column(
            modifier = Modifier
                .align(Alignment.TopStart)
                .padding(14.dp)
                .background(Color(0xAA08141A), RoundedCornerShape(18.dp))
                .padding(horizontal = 14.dp, vertical = 10.dp),
            verticalArrangement = Arrangement.spacedBy(4.dp)
        ) {
            Text(
                text = if (mode == ScanMode.SetMaster) "Align master barcode in frame" else "Align verify barcode in frame",
                color = Color.White,
                style = MaterialTheme.typography.labelLarge,
                fontWeight = FontWeight.SemiBold
            )
            Text(
                text = if (barcodes.isEmpty()) "No barcode locked yet" else "Barcode locked${lastReadValue?.let { ": ${it.take(22)}" } ?: ""}",
                color = Color.White.copy(alpha = 0.8f),
                style = MaterialTheme.typography.bodyMedium
            )
        }
    }
}

private fun mapToOverlayBarcode(
    rawValue: String,
    left: Float,
    top: Float,
    right: Float,
    bottom: Float,
    sourceWidth: Float,
    sourceHeight: Float,
    rotationDegrees: Int
): OverlayBarcode? {
    val normalized = when (rotationDegrees) {
        0 -> OverlayBarcode(
            rawValue = rawValue,
            left = left / sourceWidth,
            top = top / sourceHeight,
            right = right / sourceWidth,
            bottom = bottom / sourceHeight
        )

        90 -> OverlayBarcode(
            rawValue = rawValue,
            left = top / sourceHeight,
            top = 1f - (right / sourceWidth),
            right = bottom / sourceHeight,
            bottom = 1f - (left / sourceWidth)
        )

        180 -> OverlayBarcode(
            rawValue = rawValue,
            left = 1f - (right / sourceWidth),
            top = 1f - (bottom / sourceHeight),
            right = 1f - (left / sourceWidth),
            bottom = 1f - (top / sourceHeight)
        )

        270 -> OverlayBarcode(
            rawValue = rawValue,
            left = 1f - (bottom / sourceHeight),
            top = left / sourceWidth,
            right = 1f - (top / sourceHeight),
            bottom = right / sourceWidth
        )

        else -> null
    } ?: return null

    return normalized.copy(
        left = normalized.left.coerceIn(0f, 1f),
        top = normalized.top.coerceIn(0f, 1f),
        right = normalized.right.coerceIn(0f, 1f),
        bottom = normalized.bottom.coerceIn(0f, 1f)
    )
}

@Composable
private fun ScannerHistoryPane(
    logs: List<ScanLog>,
    modifier: Modifier
) {
    ElevatedCard(modifier = modifier) {
        Column(
            modifier = Modifier.fillMaxSize().padding(20.dp),
            verticalArrangement = Arrangement.spacedBy(16.dp)
        ) {
            Text("Recent scans", style = MaterialTheme.typography.headlineSmall)
            if (logs.isEmpty()) {
                MessagePane("No scan history", "Verified scans will appear here as soon as the camera reads a barcode.", Modifier.fillMaxWidth())
            } else {
                LazyColumn(verticalArrangement = Arrangement.spacedBy(12.dp)) {
                    items(logs) { log ->
                        Card {
                            Column(Modifier.fillMaxWidth().padding(16.dp), verticalArrangement = Arrangement.spacedBy(6.dp)) {
                                Text(
                                    if (log.matched) "PASS" else "FAIL",
                                    style = MaterialTheme.typography.titleLarge,
                                    color = if (log.matched) MaterialTheme.colorScheme.primary else MaterialTheme.colorScheme.error
                                )
                                Text("Master: ${log.masterCode}")
                                Text("Read: ${log.readValue}")
                                Text(formatTimestamp(log.createdAt), color = MaterialTheme.colorScheme.onSurfaceVariant)
                            }
                        }
                    }
                }
            }
        }
    }
}
