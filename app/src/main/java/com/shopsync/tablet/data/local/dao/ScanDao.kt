package com.shopsync.tablet.data.local.dao

import androidx.room.Dao
import androidx.room.Insert
import androidx.room.Query
import com.shopsync.tablet.data.local.entity.ScanLogEntity
import kotlinx.coroutines.flow.Flow

@Dao
interface ScanDao {
    @Query("SELECT * FROM scan_log ORDER BY createdAt DESC LIMIT 30")
    fun observeRecentScans(): Flow<List<ScanLogEntity>>

    @Query("SELECT COUNT(*) FROM scan_log WHERE createdAt >= :since")
    suspend fun recentScanCount(since: Long): Int

    @Insert
    suspend fun insertScan(scan: ScanLogEntity): Long
}
