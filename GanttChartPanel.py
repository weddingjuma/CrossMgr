import wx
import random
import math
import sys
import bisect
import datetime
import Utils

havePopupWindow = 1
if wx.Platform == '__WXMAC__':
	havePopupWindow = 0
	wx.PopupWindow = wx.PopupTransientWindow = wx.Window
	
class BarInfoPopup( wx.PopupTransientWindow ):
	"""Shows Specific Rider and Lap information."""
	def __init__(self, parent, style, text):
		wx.PopupTransientWindow.__init__(self, parent, style)
		self.SetBackgroundColour(wx.WHITE)
		border = 10
		st = wx.StaticText(self, -1, text, pos=(border/2,border/2))
		sz = st.GetBestSize()
		self.SetSize( (sz.width+border, sz.height+border) )
		
def SetScrollbarParameters( sb, thumbSize, range, pageSize  ):
	sb.SetScrollbar( min(sb.GetThumbPosition(), range - thumbSize), thumbSize, range, pageSize )

def makeColourGradient(frequency1, frequency2, frequency3,
                        phase1, phase2, phase3,
                        center = 128, width = 127, len = 50 ):
	fp = [(frequency1,phase1), (frequency2,phase2), (frequency3,phase3)]	
	grad = [wx.Colour(*[math.sin(f*i + p) * width + center for f, p in fp]) for i in xrange(len)]
	return grad
	
def makePastelColours( len = 50 ):
	return makeColourGradient(2.4,2.4,2.4,0,2,4,128,127,len)

def lighterColour( c ):
	rgb = c.Get( False )
	return wx.Colour( *[int(v + (255 - v) * 0.6) for v in rgb] )

def numFromLabel( s ):
	lastSpace = s.rfind( ' ' )
	if lastSpace >= 0:
		try:
			return int(s[lastSpace+1:])
		except ValueError:
			pass
	firstSpace = s.find( ' ' )
	if firstSpace < 0:
		return int(s)
	return int(s[:firstSpace])
	
class GanttChartPanel(wx.PyPanel):
	def __init__(self, parent, id=wx.ID_ANY, pos=wx.DefaultPosition,
				size=wx.DefaultSize, style=wx.NO_BORDER,
				name="GanttChartPanel" ):
		"""
		Default class constructor.
		"""
		wx.PyPanel.__init__(self, parent, id, pos, size, style, name)
		self.SetBackgroundColour(wx.WHITE)
		self.data = None
		self.labels = None
		self.greyOutSet = None
		self.nowTime = None
		self.numSelect = None
		self.dClickCallback = None
		self.rClickCallback = None
		self.getNowTimeCallback = None
		self.minimizeLabels = False
		
		self.horizontalSB = wx.ScrollBar( self, wx.ID_ANY, style=wx.SB_HORIZONTAL )
		self.horizontalSB.Bind( wx.EVT_SCROLL, self.OnHorizontalScroll )
		self.verticalSB = wx.ScrollBar( self, wx.ID_ANY, style=wx.SB_VERTICAL )
		self.verticalSB.Bind( wx.EVT_SCROLL, self.OnVerticalScroll )
		self.scrollbarWidth = 16
		self.horizontalSB.Show( False )
		self.verticalSB.Show( False )
		
		self.colours = makeColourGradient(2.4,2.4,2.4,0,2,4,128,127,500)
		self.lighterColours = [lighterColour(c) for c in self.colours]
			
		# Bind the events related to our control: first of all, we use a
		# combination of wx.BufferedPaintDC and an empty handler for
		# wx.EVT_ERASE_BACKGROUND (see later) to reduce flicker
		self.Bind(wx.EVT_PAINT, self.OnPaint)
		self.Bind(wx.EVT_ERASE_BACKGROUND, self.OnEraseBackground)
		self.Bind(wx.EVT_SIZE, self.OnSize)
		self.Bind(wx.EVT_LEFT_UP, self.OnLeftClick)
		self.Bind(wx.EVT_LEFT_DCLICK, self.OnLeftDClick)
		self.Bind(wx.EVT_RIGHT_UP, self.OnRightClick)
		
		self.Bind(wx.EVT_MOUSEWHEEL, self.OnWheel )

	def OnWheel( self, event ):
		if not self.verticalSB.IsShown():
			return
		amt = event.GetWheelRotation()
		units = -amt / event.GetWheelDelta()
		sb = self.verticalSB
		pos = sb.GetThumbPosition() + units
		pos = min( max( pos, 0 ), sb.GetRange() - sb.GetThumbSize() )
		if pos != sb.GetThumbPosition():
			sb.SetThumbPosition( pos )
			self.OnVerticalScroll( event )
		
	def DoGetBestSize(self):
		return wx.Size(128, 100)

	def SetForegroundColour(self, colour):
		wx.PyPanel.SetForegroundColour(self, colour)
		self.Refresh()
		
	def SetBackgroundColour(self, colour):
		wx.PyPanel.SetBackgroundColour(self, colour)
		self.Refresh()
		
	def GetDefaultAttributes(self):
		"""
		Overridden base class virtual.  By default we should use
		the same font/colour attributes as the native wx.StaticText.
		"""
		return wx.StaticText.GetClassDefaultAttributes()

	def ShouldInheritColours(self):
		"""
		Overridden base class virtual.  If the parent has non-default
		colours then we want this control to inherit them.
		"""
		return True

	def SetData( self, data, labels = None, nowTime = None, interp = None, greyOutSet = set() ):
		"""
		* data is a list of lists.  Each list is a list of times.		
		* labels are the names of the series.  Optional.
		"""
		self.data = None
		self.labels = None
		self.nowTime = None
		self.greyOutSet = greyOutSet
		if data and any( s for s in data ):
			self.data = data
			self.dataMax = max(max(s) if s else -sys.float_info.max for s in self.data)
			if labels:
				self.labels = [str(lab) for lab in labels]
				if len(self.labels) < len(self.data):
					self.labels = self.labels + [None] * (len(self.data) - len(self.labels))
				elif len(self.labels) > len(self.data):
					self.labels = self.labels[:len(self.data)]
			else:
				self.labels = [''] * len(data)
			self.nowTime = nowTime
			
		self.interp = interp
		self.Refresh()
	
	def OnPaint(self, event ):
		#dc = wx.PaintDC(self)
		dc = wx.BufferedPaintDC(self)
		self.Draw(dc)

	def OnVerticalScroll( self, event ):
		dc = wx.ClientDC(self)
		if not self.IsDoubleBuffered():
			dc = wx.BufferedDC( dc )
		self.Draw( dc )
		
	def OnHorizontalScroll( self, event ):
		self.OnVerticalScroll( event )
		
	def OnSize(self, event):
		self.Refresh()
	
	def OnLeftDClick( self, event ):
		if getattr(self, 'empty', True):
			return
		if self.numSelect is not None:
			if self.dClickCallback:
				self.dClickCallback( self.numSelect )
	
	def getRiderLap( self, event ):
		x, y = event.GetPositionTuple()
		y -= self.barHeight
		x -= self.labelsWidthLeft
		iRider = int(y / self.barHeight)
		if self.verticalSB.IsShown():
			iRider += self.verticalSB.GetThumbPosition()
		if not 0 <= iRider < len(self.data):
			return None, None

		t = x / self.xFactor
		if self.horizontalSB.IsShown():
			t += self.horizontalSB.GetThumbPosition()
		iLap = bisect.bisect_left( self.data[iRider], t )
		if not 1 <= iLap < len(self.data[iRider]):
			return iRider, None
			
		return iRider, iLap
	
	def OnLeftClick( self, event ):
		if getattr(self, 'empty', True):
			return
			
		iRider, iLap = self.getRiderLap( event )
		if iRider is None:
			return
		
		if getattr(self, 'iRiderLast', -1) == iRider and getattr(self, 'iLapLast', -1) == iLap:
			self.iRiderLast = -1
			self.iLapLast = -1
			if getattr(self, 'lastClickTime', None) != None:
				dt = datetime.datetime.now() - getattr(self, 'lastClickTime')
				if dt.total_seconds() < 0.5 and self.dClickCallback:
					self.dClickCallback( self.numSelect )
			self.lastClickTime = None
			return
		self.iRiderLast = iRider
		self.iLapLast = iLap
		self.lastClickTime = datetime.datetime.now()
		
		self.numSelect = numFromLabel( self.labels[iRider] )
		if self.getNowTimeCallback:
			self.nowTime = self.getNowTimeCallback()
		self.Refresh()
		
		if iLap is None:
			return

		tLapStart = self.data[iRider][iLap-1]
		tLapEnd = self.data[iRider][iLap]
		bip = BarInfoPopup(self, wx.SIMPLE_BORDER,
								'Rider: %s  Lap: %d\nLap Start:  %s Lap End: %s\nLap Time: %s' %
								(self.labels[iRider] if self.labels else str(iRider), iLap,
								Utils.formatTime(tLapStart),
								Utils.formatTime(tLapEnd),
								Utils.formatTime(tLapEnd - tLapStart)))

		xPos, yPos = event.GetPositionTuple()
		width, height = bip.GetClientSize()
		pos = self.ClientToScreen( (xPos - width - 2, yPos - height - 2) )
		bip.Position( pos, (0,0) )
		bip.Popup()
	
	def OnRightClick( self, event ):
		if getattr(self, 'empty', True):
			return
			
		iRider, iLap = self.getRiderLap( event )
		if iRider is None:
			return
			
		self.numSelect = numFromLabel(self.labels[iRider])
		if self.getNowTimeCallback:
			self.nowTime = self.getNowTimeCallback()
		self.Refresh()
		
		if iLap is None:
			return
		rClickCallback = getattr(self, 'rClickCallback', None)
		if rClickCallback is not None:
			xPos, yPos = event.GetPositionTuple()
			rClickCallback( xPos, yPos, self.numSelect, iRider, iLap )
	
	def Draw( self, dc ):
		size = self.GetClientSize()
		width = size.width
		height = size.height
		
		minBarWidth = 48
		minBarHeight = 18
		maxBarHeight = 28
		
		backColour = self.GetBackgroundColour()
		backBrush = wx.Brush(backColour, wx.SOLID)
		greyBrush = wx.Brush( wx.Colour(196+32,196+32,196+32), wx.SOLID )
		backPen = wx.Pen(backColour, 0)
		dc.SetBackground(backBrush)
		dc.Clear()
		
		if not self.data or self.dataMax == 0 or width < 50 or height < 50:
			self.empty = True
			self.verticalSB.Show( False )
			self.horizontalSB.Show( False )
			return
			
		self.empty = False
		
		barHeight = int(float(height) / float(len(self.data) + 2))
		barHeight = max( barHeight, minBarHeight )
		barHeight = min( barHeight, maxBarHeight )
		font = wx.FontFromPixelSize( wx.Size(0,barHeight - 1), wx.FONTFAMILY_SWISS, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_NORMAL )
		dc.SetFont( font )
		textWidthLeftMax, textHeightMax = dc.GetTextExtent( '0000' )
		textWidthRightMax = textWidthLeftMax
		for label in self.labels:
			textWidthLeftMax = max( textWidthLeftMax, dc.GetTextExtent(label)[0] )
			textWidthRightMax = max( textWidthRightMax, dc.GetTextExtent( str(numFromLabel(label)) )[0] )
				
		if textWidthLeftMax + textWidthRightMax > width:
			self.horizontalSB.Show( False )
			self.verticalSB.Show( False )
			self.empty = True
			return
		
		maxLaps = max( len(d) for d in self.data )
		if maxLaps and (width - textWidthLeftMax - textWidthRightMax) / maxLaps < minBarWidth:
			self.horizontalSB.Show( True )
		else:
			self.horizontalSB.Show( False )
		
		if self.horizontalSB.IsShown():
			height -= self.scrollbarWidth
			
		barHeight = int(float(height) / float(len(self.data) + 2))
		barHeight = max( barHeight, minBarHeight )
		barHeight = min( barHeight, maxBarHeight )
		drawHeight = height - 2 * barHeight
		if barHeight * len(self.data) > drawHeight:
			self.verticalSB.Show( True )
			self.verticalSB.SetPosition( (width - self.scrollbarWidth, barHeight) )
			self.verticalSB.SetSize( (self.scrollbarWidth, drawHeight) )
			pageSize = int(drawHeight / barHeight)
			SetScrollbarParameters( self.verticalSB, pageSize-1, len(self.data)-1, pageSize )
		else:
			self.verticalSB.Show( False )
			
		if self.verticalSB.IsShown():
			width -= self.scrollbarWidth
			
		iDataShowStart = self.verticalSB.GetThumbPosition() if self.verticalSB.IsShown() else 0
		iDataShowEnd = iDataShowStart + self.verticalSB.GetThumbSize() + 1 if self.verticalSB.IsShown() else len(self.data)
		tShowStart = self.horizontalSB.GetThumbPosition() if self.horizontalSB.IsShown() else 0

		font = wx.FontFromPixelSize( wx.Size(0,barHeight - 1), wx.FONTFAMILY_SWISS, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_NORMAL )
		dc.SetFont( font )
		textWidthLeftMax, textHeightMax = dc.GetTextExtent( '0000' )
		textWidthRightMax = textWidthLeftMax
		for label in self.labels:
			textWidthLeftMax = max( textWidthLeftMax, dc.GetTextExtent(label)[0] )
			textWidthRightMax = max( textWidthRightMax, dc.GetTextExtent( str(numFromLabel(label)) )[0] )
				
		if textWidthLeftMax + textWidthRightMax > width:
			self.horizontalSB.Show( False )
			self.verticalSB.Show( False )
			self.empty = True
			return

		
		legendSep = 4			# Separations between legend entries and the Gantt bars.
		labelsWidthLeft = textWidthLeftMax + legendSep
		labelsWidthRight = textWidthRightMax + legendSep
			
		'''
		if labelsWidthLeft > width / 2:
			labelsWidthLeft = 0
			labelsWidthRight = 0
			drawLabels = False
		'''

		xLeft = labelsWidthLeft
		xRight = width - labelsWidthRight
		yBottom = min( barHeight * (len(self.data) + 1), barHeight + drawHeight )
		yTop = barHeight

		if self.horizontalSB.IsShown():
			viewWidth = minBarWidth * maxLaps
			ratio = float(xRight - xLeft) / float(viewWidth)
			sbMax = int(self.dataMax) + 1
			pageSize = int(sbMax * ratio)
			SetScrollbarParameters( self.horizontalSB, pageSize-1, sbMax, pageSize )
			self.horizontalSB.SetPosition( (labelsWidthLeft, height) )
			self.horizontalSB.SetSize( (xRight - xLeft, self.scrollbarWidth) )
		
		fontLegend = wx.FontFromPixelSize( wx.Size(0,barHeight*.75), wx.FONTFAMILY_SWISS, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_NORMAL )
		dc.SetFont( fontLegend )
		textWidth, textHeight = dc.GetTextExtent( '00:00' if self.dataMax < 60*60 else '00:00:00' )
			
		# Draw the horizontal labels.
		# Find some reasonable tickmarks for the x axis.
		numLabels = (xRight - xLeft) / (textWidth * 1.5)
		tView = self.dataMax if not self.horizontalSB.IsShown() else self.horizontalSB.GetThumbSize()
		d = tView / float(numLabels)
		intervals = [1, 2, 5, 10, 15, 20, 30, 1*60, 2*60, 5*60, 10*60, 15*60, 20*60, 30*60, 1*60*60, 2*60*60, 4*60*60, 8*60*60, 12*60*60, 24*60*60]
		d = intervals[bisect.bisect_left(intervals, d, 0, len(intervals)-1)]
		if self.horizontalSB.IsShown():
			tAdjust = self.horizontalSB.GetThumbPosition()
			viewWidth = minBarWidth * maxLaps
			dFactor = float(viewWidth) / float(self.dataMax)
		else:
			tAdjust = 0
			dFactor = (xRight - xLeft) / float(self.dataMax)
		dc.SetPen(wx.Pen(wx.BLACK, 1))
		
		for t in xrange(0, int(self.dataMax), d):
			x = xLeft + (t-tAdjust) * dFactor
			if x < xLeft:
				continue
			if x > xRight:
				break
			if t < 60*60:
				s = '%d:%02d' % ((t / 60), t%60)
			else:
				s = '%d:%02d:%02d' % (t/(60*60), (t / 60)%60, t%60)
			w, h = dc.GetTextExtent(s)
			xText = x - w/2
			#xText = x
			dc.DrawText( s, xText, 0 + 4 )
			dc.DrawText( s, xText, yBottom + 4)
			dc.DrawLine( x, yBottom+3, x, yTop-3 )
		
		# Draw the Gantt chart.
		dc.SetFont( font )
		textWidth, textHeight = dc.GetTextExtent( '0000' )

		penBar = wx.Pen( wx.Colour(128,128,128), 1 )
		penBar.SetCap( wx.CAP_BUTT )
		penBar.SetJoin( wx.JOIN_MITER )
		dc.SetPen( penBar )
		
		brushBar = wx.Brush( wx.BLACK )
		transparentBrush = wx.Brush( wx.WHITE, style = wx.TRANSPARENT )
		
		ctx = wx.GraphicsContext_Create(dc)
		ctx.SetPen( wx.Pen(wx.BLACK, 1) )
		
		xyInterp = []
		
		xFactor = dFactor
		yLast = barHeight
		yHighlight = None
		
		dy = 0
		for i, s in enumerate(self.data):
			if not( iDataShowStart <= i < iDataShowEnd ):
				continue
			yCur = yLast + barHeight
			xLast = labelsWidthLeft
			xCur = xLast
			for j, t in enumerate(s):
				if xLast >= xRight:
					break
				xCur = xOriginal = int(labelsWidthLeft + (t-tAdjust) * xFactor)
				if xCur <= xLast:
					continue
				if xCur > xRight:
					xCur = xRight
				if j == 0:
					brushBar.SetColour( wx.WHITE )
					dc.SetBrush( brushBar )
					dc.DrawRectangle( xLast, yLast, xCur - xLast + 1, yCur - yLast + 1 )
				else:
					ctx.SetPen( wx.Pen(wx.WHITE, 1, style=wx.TRANSPARENT ) )
					dy = yCur - yLast + 1
					dd = int(dy * 0.3)
					ic = j % len(self.colours)
					
					b1 = ctx.CreateLinearGradientBrush(0, yLast,      0, yLast + dd + 1, self.colours[ic], self.lighterColours[ic])
					ctx.SetBrush(b1)
					ctx.DrawRectangle(xLast, yLast     , xCur - xLast + 1, dd + 1)
					
					b2 = ctx.CreateLinearGradientBrush(0, yLast + dd, 0, yLast + dy, self.lighterColours[ic], self.colours[ic])
					ctx.SetBrush(b2)
					ctx.DrawRectangle(xLast, yLast + dd, xCur - xLast + 1, dy-dd )
					
					dc.SetBrush( transparentBrush )
					dc.SetPen( penBar )
					dc.DrawRectangle( xLast, yLast, xCur - xLast + 1, dy )
					
					try:
						if self.interp and self.interp[i][j] and xOriginal <= xRight:
							xyInterp.append( (xOriginal, yLast) )
					except IndexError:
						pass

				xLast = xCur
			
			# Draw the last empty bar.
			xCur = int(labelsWidthLeft + self.dataMax * xFactor)
			if xCur > xRight:
				xCur = xRight
			dc.SetPen( penBar )
			brushBar.SetColour( wx.WHITE )
			dc.SetBrush( brushBar )
			dc.DrawRectangle( xLast, yLast, xCur - xLast + 1, yCur - yLast + 1 )
			
			# Draw the label on both ends.
			if self.greyOutSet and i in self.greyOutSet:
				dc.SetPen( wx.TRANSPARENT_PEN )
				dc.SetBrush( greyBrush )
				dc.DrawRectangle( 0, yLast, textWidthLeftMax, yCur - yLast + 1 )
				dc.SetBrush( backBrush )
			labelWidth = dc.GetTextExtent( self.labels[i] )[0]
			dc.DrawText( self.labels[i], textWidthLeftMax - labelWidth, yLast )
			if not self.minimizeLabels:
				label = self.labels[i]
				lastSpace = label.rfind( ' ' )
				if lastSpace > 0:
					label = label[lastSpace+1:]
				dc.DrawText( label, width - labelsWidthRight + legendSep, yLast )

			if str(self.numSelect) == str(numFromLabel(self.labels[i])):
				yHighlight = yCur

			yLast = yCur
				
		if yHighlight is not None and len(self.data) > 1:
			dc.SetPen( wx.Pen(wx.BLACK, 2) )
			dc.SetBrush( wx.TRANSPARENT_BRUSH )
			dc.DrawLine( 0, yHighlight, width, yHighlight )
			yHighlight -= barHeight
			dc.DrawLine( 0, yHighlight, width, yHighlight )
		
		# Draw indicators for interpolated values.
		radius = (dy/2) * 0.9
		
		# Define a path for the indicator about the origin.
		ctx.SetPen( penBar )
		ctx.SetBrush( ctx.CreateRadialGradientBrush( 0, - radius*0.50, 0, 0, radius + 1, wx.WHITE, wx.Colour(220,220,0) ) )
		path = ctx.CreatePath()
		path.MoveToPoint( 0, -radius )
		path.AddLineToPoint( -radius, 0 )
		path.AddLineToPoint( 0, radius )
		path.AddLineToPoint( radius, 0 )
		path.AddLineToPoint( 0, -radius )

		# Draw the interp indicators.
		for xSphere, ySphere in xyInterp:
			ctx.PushState()
			ctx.Translate( xSphere, ySphere + dy/2.0 - (dy/2.0 - radius) / 4 )
			ctx.DrawPath( path )
			ctx.PopState()
		
		# Draw the now timeline.
		if self.nowTime and self.nowTime < self.dataMax:
			nowTimeStr = Utils.formatTime( self.nowTime )
			labelWidth, labelHeight = dc.GetTextExtent( nowTimeStr )	
			x = int(labelsWidthLeft + (self.nowTime - tAdjust) * xFactor)
			
			ntColour = '#339966'
			dc.SetPen( wx.Pen(ntColour, 6) )
			dc.DrawLine( x, barHeight - 4, x, yLast + 4 )
			dc.SetPen( wx.Pen(wx.WHITE, 2) )
			dc.DrawLine( x, barHeight - 4, x, yLast + 4 )
			
			dc.SetBrush( wx.Brush(ntColour) )
			dc.SetPen( wx.Pen(ntColour,1) )
			rect = wx.Rect( x - labelWidth/2-2, 0, labelWidth+4, labelHeight )
			dc.DrawRectangleRect( rect )
			if not self.minimizeLabels:
				rect.SetY( yLast+2 )
				dc.DrawRectangleRect( rect )

			dc.SetTextForeground( wx.WHITE )
			dc.DrawText( nowTimeStr, x - labelWidth / 2, 0 )
			if not self.minimizeLabels:
				dc.DrawText( nowTimeStr, x - labelWidth / 2, yLast + 2 )

		self.xFactor = xFactor
		self.barHeight = barHeight
		self.labelsWidthLeft = labelsWidthLeft

			
	def OnEraseBackground(self, event):
		# This is intentionally empty, because we are using the combination
		# of wx.BufferedPaintDC + an empty OnEraseBackground event to
		# reduce flicker
		pass
		
if __name__ == '__main__':
	def GetData():
		data = []
		interp = []
		for i in xrange(40):
			data.append( [t + i*10 for t in xrange(0, 60*60 * 3, 7*60)] )
			interp.append( [((t + i*10)%100)//10 for t in xrange(0, 60*60 * 3, 7*60)] )
		return data, interp

	app = wx.PySimpleApp()
	mainWin = wx.Frame(None,title="GanttChartPanel", size=(600,400))
	gantt = GanttChartPanel(mainWin)

	random.seed( 10 )
	t = 55*60
	tVar = t * 0.15
	data, interp = GetData()
	gantt.SetData( data, [str(i) for i in xrange(100, 100+len(data))], interp = interp )

	mainWin.Show()
	app.MainLoop()