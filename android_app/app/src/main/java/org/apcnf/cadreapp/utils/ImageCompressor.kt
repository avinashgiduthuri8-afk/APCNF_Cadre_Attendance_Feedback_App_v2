package org.apcnf.cadreapp.utils

import android.content.Context
import android.graphics.Bitmap
import android.graphics.BitmapFactory
import android.graphics.Matrix
import android.net.Uri
import android.util.Base64
import androidx.exifinterface.media.ExifInterface
import java.io.ByteArrayOutputStream
import java.io.File
import java.io.InputStream
import kotlin.math.max

object ImageCompressor {

    private const val MAX_DIMENSION = 1024
    private const val JPEG_QUALITY = 75

    /**
     * Reads an image file, corrects EXIF orientation, scales to max 1024px,
     * and compresses to JPEG Base64 string.
     */
    fun compressImageToBase64(imageFile: File): String {
        val boundsOptions = BitmapFactory.Options().apply {
            inJustDecodeBounds = true
        }
        BitmapFactory.decodeFile(imageFile.absolutePath, boundsOptions)

        val originalWidth = boundsOptions.outWidth
        val originalHeight = boundsOptions.outHeight
        val maxDim = max(originalWidth, originalHeight)

        var sampleSize = 1
        while ((maxDim / sampleSize) > (MAX_DIMENSION * 1.5)) {
            sampleSize *= 2
        }

        val decodeOptions = BitmapFactory.Options().apply {
            inSampleSize = sampleSize
            inPreferredConfig = Bitmap.Config.RGB_565 // Lowers memory footprint
        }

        val decodedBitmap = BitmapFactory.decodeFile(imageFile.absolutePath, decodeOptions)
            ?: throw IllegalStateException("Failed to decode camera image file.")

        // Correct rotation based on EXIF
        val orientedBitmap = fixOrientation(imageFile.absolutePath, decodedBitmap)

        // Scale precisely if still larger than MAX_DIMENSION
        val finalBitmap = scaleDown(orientedBitmap, MAX_DIMENSION)

        val outputStream = ByteArrayOutputStream()
        finalBitmap.compress(Bitmap.CompressFormat.JPEG, JPEG_QUALITY, outputStream)
        val imageBytes = outputStream.toByteArray()

        return "data:image/jpeg;base64," + Base64.encodeToString(imageBytes, Base64.NO_WRAP)
    }

    private fun scaleDown(bitmap: Bitmap, maxDim: Int): Bitmap {
        val width = bitmap.width
        val height = bitmap.height

        if (width <= maxDim && height <= maxDim) {
            return bitmap
        }

        val ratio = width.toFloat() / height.toFloat()
        val targetWidth: Int
        val targetHeight: Int

        if (ratio > 1) {
            targetWidth = maxDim
            targetHeight = (maxDim / ratio).toInt()
        } else {
            targetHeight = maxDim
            targetWidth = (maxDim * ratio).toInt()
        }

        return Bitmap.createScaledBitmap(bitmap, targetWidth, targetHeight, true)
    }

    private fun fixOrientation(filePath: String, bitmap: Bitmap): Bitmap {
        return try {
            val exif = ExifInterface(filePath)
            val orientation = exif.getAttributeInt(
                ExifInterface.TAG_ORIENTATION,
                ExifInterface.ORIENTATION_NORMAL
            )
            val matrix = Matrix()
            when (orientation) {
                ExifInterface.ORIENTATION_ROTATE_90 -> matrix.postRotate(90f)
                ExifInterface.ORIENTATION_ROTATE_180 -> matrix.postRotate(180f)
                ExifInterface.ORIENTATION_ROTATE_270 -> matrix.postRotate(270f)
                else -> return bitmap
            }
            Bitmap.createBitmap(bitmap, 0, 0, bitmap.width, bitmap.height, matrix, true)
        } catch (e: Exception) {
            bitmap
        }
    }
}
