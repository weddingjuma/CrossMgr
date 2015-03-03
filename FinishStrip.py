import wx
import os
import sys
import glob
import math
import Utils

def formatTime( t ):
	return Utils.formatTime( t, highPrecision=True, forceHours=False, forceMinutes=False )

contrastColour = wx.Colour( 255, 130, 0 )

photoWidth = 640
photoHeight = 480

DefaultPhotoFolder = 'CrossMgrCamera/Test_Photos'
DefaultPhotoFolder = 'BCC_Test_Photos'
DefaultPhotoFolder = 'PhotoExample'

class PhotoExists( wx.Panel ):
	def __init__( self, parent, id=wx.ID_ANY, size=(640,480), style=0,
			tMin= 0, tMax=600.0, pixelsPerSec = 1.0, tPhotos = [] ):
		super(PhotoExists, self).__init__( parent, id, size=size, style=style )
		self.SetBackgroundStyle( wx.BG_STYLE_CUSTOM )
		self.tMin = tMin
		self.tMax = tMax
		self.tPhotos = tPhotos
		self.pixelsPerSec = pixelsPerSec
		
		self.Bind( wx.EVT_PAINT, self.OnPaint )
		self.Bind( wx.EVT_SIZE, self.OnSize )
		self.Bind( wx.EVT_ERASE_BACKGROUND, self.OnErase )

	def SetTimeMinMax( self, tMin, tMax ):
		if tMin is not None:
			self.tMin = tMin
			self.tMax = tMax
		else:
			self.tPhotos = []
		wx.CallAfter( self.Refresh )
	
	def SetTimePhotos( self, tPhotos ):
		self.tPhotos = tPhotos
		wx.CallAfter( self.Refresh )
		
	def SetPixelsPerSec( self, pixelsPerSec ):
		self.pixelsPerSec = pixelsPerSec
		wx.CallAfter( self.Refresh )
	
	def OnErase( self, event ):
		pass
	
	def OnSize( self, event ):
		wx.CallAfter( self.Refresh )
		event.Skip()
		
	def OnPaint( self, event=None ):
		dc = wx.AutoBufferedPaintDC( self )
		dc.SetBackground( wx.Brush(self.GetBackgroundColour()) )
		dc.Clear()
		
		if not self.tPhotos:
			return
		
		w, h = self.GetSize()
		x = 12
		w -= x * 2
		mult = float(w) / float(self.tMax - self.tMin)
		
		photoWidthUpdate = w * (float(photoWidth)/self.pixelsPerSec) / float(self.tMax - self.tMin)
		
		dc.SetPen( wx.Pen(wx.Colour(64,64,64), max(1, photoWidthUpdate)) )
		for t in self.tPhotos:
			tx = x + int((t - self.tMin) * mult)
			dc.DrawLine( tx, 0, tx, h )

class FinishStrip( wx.Panel ):
	def __init__( self, parent, id=wx.ID_ANY, size=(photoWidth,480), style=0,
			fps=25,
			photoFolder=DefaultPhotoFolder,
			leftToRight=False ):
		super(FinishStrip, self).__init__( parent, id, size=size, style=style )
		self.SetBackgroundStyle( wx.BG_STYLE_CUSTOM )
		
		self.fps = float(fps)
		self.scale = 1.0
		self.clip = 0.0
		self.xTimeLine = None
		
		self.Bind( wx.EVT_PAINT, self.OnPaint )
		self.Bind( wx.EVT_SIZE, self.OnSize )
		self.Bind( wx.EVT_ERASE_BACKGROUND, self.OnErase )
		self.Bind( wx.EVT_LEFT_DOWN, self.OnLeftDown )
		self.Bind( wx.EVT_LEFT_UP, self.OnLeftUp )
		
		self.Bind( wx.EVT_ENTER_WINDOW, self.OnEnterWindow )
		self.Bind( wx.EVT_MOTION, self.OnMotion )
		self.Bind( wx.EVT_LEAVE_WINDOW, self.OnLeaveWindow )
		self.xMotionLast = None
		self.yMotionLast = None
		
		self.photoFolder = photoFolder
		self.timeBitmaps = []
		
		self.leftToRight = leftToRight
		self.tDrawStart = 0.0
		self.pixelsPerSec = 25
		
		self.tDrawStartCallback = None
		
		self.RefreshBitmaps()
		
		tMin, tMax = self.GetTimeMinMax()
		if tMin is not None:
			self.tDrawStart = tMin
		
	def SetLeftToRight( self, leftToRight=True ):
		self.leftToRight = leftToRight
		wx.CallAfter( self.Refresh )
		
	def SetPixelsPerSec( self, pixelsPerSec ):
		self.pixelsPerSec = pixelsPerSec
		wx.CallAfter( self.Refresh )

	def SetDrawStartTime( self, tDrawStart ):
		self.tDrawStart = tDrawStart
		wx.CallAfter( self.Refresh )
		
	def SetClip( self, clip ):
		self.clip = clip
		wx.CallAfter( self.Refresh )
		
	def GetTimeMinMax( self ):
		return (self.timeBitmaps[0][0], self.timeBitmaps[-1][0]) if self.timeBitmaps else (None, None)
		
	def GetTimePhotos( self ):
		return [t for t, bm in self.timeBitmaps]
		
	def getPhotoTime( self, fname ):
		try:
			fname = os.path.splitext(os.path.basename(fname))[0]
			
			# Parse time and photo index from filename.
			tstr = fname.split( '-time-' )[1]
			hh, mm, ss, dd, ii = tstr.split( '-' )
			t = float(hh)*60.0*60.0 + float(mm)*60.0 + float('{}.{}'.format(ss,dd))
			ii = float(ii) - 1.0
		except Exception as e:
			return None
			
		# Round to nearest frame based on index.
		t = math.floor(t * self.fps + ii) / self.fps
		return t
		
	def RefreshBitmaps( self, tStart=0.0, tEnd=sys.float_info.max, reusePrevious=True ):
		bitmaps = {t:bm for t, bm in self.timeBitmaps} if reusePrevious else {}
		
		for f in glob.glob(os.path.join(self.photoFolder, '*.jpg')):
			t = self.getPhotoTime( f )
			if t is None or t in bitmaps or not (tStart <= t <= tEnd):
				continue
			
			image = wx.Image( f, wx.BITMAP_TYPE_JPEG )
			image.Rescale( int(image.GetWidth()*self.scale), int(image.GetHeight()*self.scale), wx.IMAGE_QUALITY_HIGH )
			bitmaps[t] = wx.BitmapFromImage( image )
		
		self.timeBitmaps = [(t, bm) for t, bm in bitmaps.iteritems()]
		self.timeBitmaps.sort( key=lambda tb: tb[0] )
		
	def OnErase( self, event ):
		pass
	
	def OnSize( self, event ):
		wx.CallAfter( self.Refresh )
		event.Skip()
		
	def getXTimeLine( self ):
		widthWin, heightWin = self.GetClientSize()
		widthWinHalf = widthWin // 2
		return min( widthWin, self.xTimeLine if self.xTimeLine is not None else widthWinHalf )
		
	def OnLeftDown( self, event ):
		self.xDragLast = event.GetX()
		self.SetCursor(wx.StockCursor(wx.CURSOR_HAND))
		event.Skip()
		
	def OnLeftUp( self, event ):
		x = event.GetX()
		self.tDrawStart += (x - self.getXTimeLine()) / float(self.pixelsPerSec) * (-1.0 if self.leftToRight else 1.0)
		self.xTimeLine = x
		wx.CallAfter( self.OnLeaveWindow )
		wx.CallAfter( self.Refresh )
		if self.tDrawStartCallback:
			wx.CallAfter( self.tDrawStartCallback, self.tDrawStart )
		self.SetCursor( wx.NullCursor )
		
	def drawXorLine( self, x, y ):
		if x is None or not self.timeBitmaps:
			return
		
		dc = wx.ClientDC( self )
		dc.SetLogicalFunction( wx.XOR )
		
		dc.SetPen( wx.WHITE_PEN )
		widthWin, heightWin = self.GetClientSize()
		widthWinHalf = widthWin // 2
		
		xTimeLine = self.getXTimeLine()
		text = formatTime( self.tDrawStart + (x - xTimeLine) / float(self.pixelsPerSec) * (-1.0 if self.leftToRight else 1.0) )
		fontHeight = max(5, heightWin//20)
		font = wx.FontFromPixelSize(
			wx.Size(0,fontHeight),
			wx.FONTFAMILY_SWISS, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD
		)
		dc.SetFont( font )
		tWidth, tHeight = dc.GetTextExtent( text )
		border = int(tHeight / 3)
		
		bm = wx.BitmapFromImage( wx.EmptyImage(tWidth, tHeight) )
		memDC = wx.MemoryDC( bm )
		memDC.SetBackground( wx.BLACK_BRUSH )
		memDC.Clear()
		memDC.SetFont( font )
		memDC.SetTextForeground( wx.WHITE )
		memDC.DrawText( text, 0, 0 )
		bmMask = wx.BitmapFromImage( bm.ConvertToImage() )
		bm.SetMask( wx.Mask(bmMask, wx.BLACK) )
		
		dc.Blit( x+border, y - tHeight, tWidth, tHeight, memDC, 0, 0, useMask=True, rop=wx.XOR )
		
		dc.DrawLine( x, 0, x, heightWin )
		
		memDC.SelectObject( wx.NullBitmap )

	def OnEnterWindow( self, event ):
		pass
		
	def OnMotion( self, event ):
		widthWin, heightWin = self.GetClientSize()
		self.drawXorLine( self.xMotionLast, self.yMotionLast )
		self.xMotionLast = event.GetX()
		self.yMotionLast = event.GetY()
		self.drawXorLine( self.xMotionLast, self.yMotionLast )
		
		if event.Dragging():
			x = event.GetX()
			dx = x - self.xDragLast
			self.tDrawStart += float(dx) / float(self.pixelsPerSec)
			self.xDragLast = x
			wx.CallAfter( self.Refresh )
		
	def OnLeaveWindow( self, event=None ):
		self.drawXorLine( self.xMotionLast, self.yMotionLast )
		self.xMotionLast = None
		
	def draw( self, dc ):
		dc.SetBackground( wx.Brush(wx.Colour(128,128,150)) )
		dc.Clear()
		
		self.xMotionLast = None
		if not self.timeBitmaps:
			return
		
		widthPhoto, heightPhoto = self.timeBitmaps[0][1].GetSize()
		xClip = int(widthPhoto * self.clip)
		widthPhoto -= xClip * 2		
		widthPhotoHalf = widthPhoto // 2
		widthWin, heightWin = self.GetClientSize()
		widthWinHalf = widthWin // 2
		
		xTimeLine = self.getXTimeLine()
		
		# Draw the composite photo.
		bitmapDC = wx.MemoryDC()
		if self.leftToRight:
			def getX( t ):
				return int(xTimeLine - widthPhotoHalf - (t - self.tDrawStart) * self.pixelsPerSec)
			
			bmRightEdge = []
			for t, bm in self.timeBitmaps:
				xLeft = getX(t)
				xRight = xLeft + widthPhoto
				if xLeft >= widthWin:
					continue
				if xRight < 0:
					break
				bmRightEdge.append( (bm, xRight) )
			bmRightEdge.append( (None, 0) )
			
			for i in xrange(0, len(bmRightEdge)-1):
				bm, xRight = bmRightEdge[i]
				bmNext, xRightNext = bmRightEdge[i+1]
				bmWidth = max( xRight - xRightNext, widthPhoto )
				bitmapDC.SelectObject( bm )
				dc.Blit(
					xRight - bmWidth, 0, bmWidth, heightPhoto,
					bitmapDC,
					widthPhoto - bmWidth + xClip, 0,
				)
				bitmapDC.SelectObject( wx.NullBitmap )
		else:
			def getX( t ):
				return int(xTimeLine - widthPhotoHalf + (t - self.tDrawStart) * self.pixelsPerSec)
			
			bmLeftEdge = []
			for t, bm in self.timeBitmaps:
				xLeft = getX(t)
				xRight = xLeft + widthPhoto
				if xRight < 0:
					continue
				if xLeft >= widthWin:
					break
				bmLeftEdge.append( (bm, xLeft) )
			bmLeftEdge.append( (None, widthWin) )
			
			for i in xrange(0, len(bmLeftEdge)-1):
				bm, xLeft = bmLeftEdge[i]
				bmNext, xLeftNext = bmLeftEdge[i+1]
				bmWidth = max( xLeftNext - xLeft, widthPhoto )
				bitmapDC.SelectObject( bm )
				dc.Blit(
					xLeft, 0, bmWidth, heightPhoto,
					bitmapDC,
					xClip, 0,
				)
				bitmapDC.SelectObject( wx.NullBitmap )
		
		# Draw the current time at the timeline.
		gc = wx.GraphicsContext.Create( dc )
		
		gc.SetPen( wx.Pen(contrastColour, 1) )
		gc.StrokeLine( xTimeLine, 0, xTimeLine, heightWin )
		
		text = formatTime( self.tDrawStart )
		fontHeight = max(5, heightWin//20)
		font = wx.FontFromPixelSize(
			wx.Size(0,fontHeight),
			wx.FONTFAMILY_SWISS, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_NORMAL
		)
		gc.SetFont( font, wx.BLACK )
		tWidth, tHeight = gc.GetTextExtent( text )
		border = int(tHeight / 3)
		
		gc.SetPen( wx.Pen(wx.Colour(64,64,64), 1) )
		gc.SetBrush( wx.Brush(wx.Colour(200,200,200)) )
		rect = wx.Rect( xTimeLine - tWidth//2 - border, 0, tWidth + border*2, tHeight + border*2 )
		gc.DrawRoundedRectangle( rect.GetLeft(), rect.GetTop(), rect.GetWidth(), rect.GetHeight(), border*1.5 )
		rect.SetTop( heightWin - tHeight - border )
		gc.DrawRoundedRectangle( rect.GetLeft(), rect.GetTop(), rect.GetWidth(), rect.GetHeight(), border*1.5 )
		
		gc.DrawText( text, xTimeLine - tWidth//2, border )
		gc.DrawText( text, xTimeLine - tWidth//2, heightWin - tHeight - border/2 )
	
	def OnPaint( self, event=None ):
		self.draw( wx.PaintDC(self) )
		
	def GetBitmap( self ):
		widthWin, heightWin = self.GetClientSize()
		bm = wx.EmptyBitmap( widthWin, heightWin )
		dc = wx.MemoryDC( bm )
		self.draw( dc )
		dc.SelectObject( wx.NullBitmap )
		return bm

class FinishStripPanel( wx.Panel ):
	def __init__( self, parent, id=wx.ID_ANY, size=wx.DefaultSize, style=0,
			fps=25.0, photoFolder=DefaultPhotoFolder ):
		super(FinishStripPanel, self).__init__( parent, id, size=size, style=style )
		
		self.fps = fps
		
		vs = wx.BoxSizer( wx.VERTICAL )
		
		displayWidth, displayHeight = wx.GetDisplaySize()
	
		self.leftToRight = True
		self.finish = FinishStrip( self, size=(0, 480), leftToRight=self.leftToRight, photoFolder=photoFolder )
		self.finish.tDrawStartCallback = self.tDrawStartCallback
		
		self.timeSlider = wx.Slider( self, style=wx.SL_HORIZONTAL, minValue=0, maxValue=displayWidth )
		self.timeSlider.SetPageSize( 1 )
		self.timeSlider.Bind( wx.EVT_SCROLL, self.onChangeTime )
		
		self.photoExists = PhotoExists( self, size=(0, 12) )
		
		minPixelsPerSecond, maxPixelsPerSecond = self.getSpeedPixelsPerSecondMinMax()
		self.speedSlider = wx.Slider( self, style=wx.SL_HORIZONTAL|wx.SL_LABELS, minValue=minPixelsPerSecond, maxValue=maxPixelsPerSecond )
		self.speedSlider.SetPageSize( 1 )
		self.speedSlider.Bind( wx.EVT_SCROLL, self.onChangeSpeed )
		
		self.clipSlider = wx.Slider( self, style=wx.SL_HORIZONTAL|wx.SL_LABELS, minValue=0, maxValue=90 )
		self.clipSlider.Bind( wx.EVT_SCROLL, self.onChangeClip )
		
		self.direction = wx.RadioBox( self,
			label=_('Direction'),
			choices=[_('Right to Left'), _('Left to Right')],
			majorDimension=1,
			style=wx.RA_SPECIFY_ROWS
		)
		self.direction.SetSelection( 1 if self.leftToRight else 0 )
		self.direction.Bind( wx.EVT_RADIOBOX, self.onDirection )

		self.copyToClipboard = wx.Button( self, label=_('Copy to Clipboard') )
		self.copyToClipboard.Bind( wx.EVT_BUTTON, self.onCopyToClipboard )
		
		self.save = wx.Button( self, label=u'{}...'.format(_('Save')) )
		self.save.Bind( wx.EVT_BUTTON, self.onSave )
		
		fgs = wx.FlexGridSizer( cols=2, vgap=4, hgap=0 )
		
		fgs.Add( wx.StaticText(self, label=u'{}:'.format(_('Time'))), flag=wx.ALIGN_RIGHT|wx.ALIGN_CENTRE_VERTICAL )
		fgs.Add( self.timeSlider, flag=wx.EXPAND )
		
		fgs.Add( wx.StaticText(self) )
		fgs.Add( self.photoExists, flag=wx.EXPAND|wx.ALIGN_CENTRE_VERTICAL )
		
		fgs.Add( wx.StaticText(self, label=u'{}:'.format(_('Pixels/Sec'))), flag=wx.ALIGN_RIGHT|wx.ALIGN_CENTRE_VERTICAL )
		fgs.Add( self.speedSlider, flag=wx.EXPAND )
		fgs.Add( wx.StaticText(self, label=u'{}:'.format(_('Clip'))), flag=wx.ALIGN_RIGHT|wx.ALIGN_CENTRE_VERTICAL )
		fgs.Add( self.clipSlider, flag=wx.EXPAND )
		
		fgs.AddGrowableCol( 1, 1 )
		
		hs = wx.BoxSizer( wx.HORIZONTAL )
		hs.Add( self.direction )
		hs.AddSpacer( 16 )
		hs.Add( self.copyToClipboard, flag=wx.ALIGN_CENTRE_VERTICAL )
		hs.AddSpacer( 4 )
		hs.Add( self.save, flag=wx.ALIGN_CENTRE_VERTICAL )
		
		vs.Add( self.finish, flag=wx.EXPAND )
		vs.Add( fgs, flag=wx.EXPAND|wx.ALL, border=4 )
		vs.Add( hs, flag=wx.EXPAND|wx.ALL, border=4 )
		
		self.SetSizer( vs )
		wx.CallAfter( self.initUI )
		
	def initUI( self ):
		self.finish.SetPixelsPerSec( self.speedSlider.GetMin() )
		self.photoExists.SetTimeMinMax( *self.getPhotoTimeMinMax() )
		self.photoExists.SetTimePhotos( self.finish.GetTimePhotos() )
		self.photoExists.SetPixelsPerSec( self.speedSlider.GetMin() )
		
	def getSpeedPixelsPerSecondMinMax( self ):
		frameTime = 1.0 / self.fps
		
		viewWidth = 4.0			# meters seen in the finish line with the finish camera
		widthPix = photoWidth	# width of the photo
		
		minMax = []
		for speedKMH in (0.0, 80.0):			# Speed of the target (km/h)
			speedMPS = speedKMH / 3.6			# Convert to m/s
			d = speedMPS * frameTime			# Distance the target moves between each frame at speed.
			pixels = widthPix * d / viewWidth	# Pixels the target moves between each frame at that speed.
			pixelsPerSecond = max(300, pixels * self.fps)
			minMax.append( int(pixelsPerSecond) )
		
		return minMax

	def onCopyToClipboard( self, event ):
		if wx.TheClipboard.Open():
			bitmapData = wx.BitmapDataObject()
			bitmapData.SetBitmap( self.finish.GetBitmap() )
			wx.TheClipboard.SetData( bitmapData )
			wx.TheClipboard.Flush() 
			wx.TheClipboard.Close()
			wx.MessageBox( _('Successfully copied to clipboard'), _('Success') )
		else:
			wx.MessageBox( _('Unable to open the clipboard'), _('Error') )

	def onSave( self, event ):
		dlg = wx.FileDialog(
			self,
			message=_('Save Finish as'),
			wildcard=u"PNG {} (*.png)|*.png".format(_("files")),
			defaultDir=os.path.dirname( Utils.getFileName() or '.' ),
			defaultFile=os.path.splitext( os.path.basename(Utils.getFileName() or _('Default.cmn')) )[0] + u'_Finish.png',
			style=wx.SAVE,
		)
		if dlg.ShowModal() == wx.ID_OK:
			fname = dlg.GetPath()
			bm = self.finish.GetBitmap()
			image = wx.ImageFromBitmap( bm )
			image.SaveFile( fname, wx.BITMAP_TYPE_PNG )
		dlg.Destroy()

	def onDirection( self, event ):
		self.SetLeftToRight( event.GetInt() == 1 ) 
		event.Skip()
		
	def onChangeSpeed( self, event ):
		self.SetPixelsPerSec( event.GetPosition(), False )
		event.Skip()
	
	def onChangeClip( self, event ):
		clip = float(event.GetPosition()) / 100.0
		self.finish.SetClip( clip )
		event.Skip()
	
	def getPhotoTimeMinMax( self ):
		tMin, tMax = self.finish.GetTimeMinMax()
		# Widen the range so we can see a few seconds before and after.
		if tMin is not None:
			tMin -= 5.0
			tMax += 5.0
		return tMin, tMax
		
	def onChangeTime( self, event ):
		r = float(event.GetPosition()) / float(event.GetEventObject().GetMax())
		tMin, tMax = self.getPhotoTimeMinMax()
		if tMin is not None:
			self.finish.SetDrawStartTime( tMin + (tMax - tMin) * r )
		event.Skip()
				
	def tDrawStartCallback( self, tDrawStart ):
		tMin, tMax = self.getPhotoTimeMinMax()
		if tMin is not None:
			vMin, vMax = self.timeSlider.GetMin(), self.timeSlider.GetMax()
			self.timeSlider.SetValue( int((tDrawStart - tMin) * float(vMax - vMin) / float(tMax - tMin)) )
			
	def SetLeftToRight( self, leftToRight ):
		self.leftToRight = leftToRight
		self.finish.SetLeftToRight( self.leftToRight )
		self.direction.SetSelection( 1 if self.leftToRight else 0 )
		
	def GetLeftToRight( self ):
		return self.leftToRight
		
	def SetPixelsPerSec( self, pixelsPerSec, setSliderValue=True ):
		self.finish.SetPixelsPerSec( pixelsPerSec )
		self.photoExists.SetPixelsPerSec( pixelsPerSec )
		if setSliderValue:
			self.speedSlider.SetValue( pixelsPerSec )
	
	def GetPixelsPerSec( self ):
		return self.speedSlider.GetValue()

class FinishStripDialog( wx.Dialog ):
	def __init__( self, parent, id=wx.ID_ANY, size=wx.DefaultSize, style=wx.DEFAULT_DIALOG_STYLE|wx.RESIZE_BORDER|wx.MAXIMIZE_BOX|wx.MINIMIZE_BOX,
			dir=None, fps=25.0, leftToRight=True, pixelsPerSec=None, photoFolder=DefaultPhotoFolder ):
			
		if size == wx.DefaultSize:
			displayWidth, displayHeight = wx.GetDisplaySize()
			width = int(displayWidth * 0.9)
			height = 730
			size = wx.Size( width, height )

		super(FinishStripDialog, self).__init__( parent, id, size=size, style=style, title=_('Finish Strip') )
		
		self.panel = FinishStripPanel( self, fps=fps, photoFolder=photoFolder )
		
		self.okButton = wx.Button( self, wx.ID_OK )
		self.okButton.SetDefault()
		
		vs = wx.BoxSizer( wx.VERTICAL )
		vs.Add( self.panel, flag=wx.EXPAND )
		vs.Add( self.okButton, flag=wx.ALIGN_CENTRE|wx.ALL, border=4 )
		self.SetSizer( vs )
		
		self.panel.SetLeftToRight( leftToRight )
		if pixelsPerSec is not None:
			self.panel.SetPixelsPerSec( pixelsPerSec )
			
	def GetAttrs( self ):
		return {
			'fps': self.panel.fps,
			'leftToRight': self.panel.GetLeftToRight(),
			'pixelsPerSec': self.panel.GetPixelsPerSec(),
		}

if __name__ == '__main__':
	app = wx.App(False)
	
	displayWidth, displayHeight = wx.GetDisplaySize()
	
	width = int(displayWidth * 0.9)
	height = 700
	
	mainWin = wx.Frame(None,title="FinishStrip", size=(width, height))
	fs = FinishStripPanel( mainWin )
	mainWin.Show()
	
	fsd = FinishStripDialog( mainWin )
	fsd.ShowModal()
	#fsd.Destroy()
	
	app.MainLoop()