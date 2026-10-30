import Foundation
import Vision
import CoreImage

let args = CommandLine.arguments
let input = URL(fileURLWithPath: args[1]), output = URL(fileURLWithPath: args[2])
let request = VNGeneratePersonSegmentationRequest()
request.qualityLevel = .accurate
request.outputPixelFormat = kCVPixelFormatType_OneComponent8
let handler = VNImageRequestHandler(url: input)
try handler.perform([request])
guard let mask = request.results?.first?.pixelBuffer else { fatalError("no person found") }
let ctx = CIContext()
let ci = CIImage(cvPixelBuffer: mask)
try ctx.writePNGRepresentation(of: ci, to: output, format: .L8, colorSpace: CGColorSpaceCreateDeviceGray())
print("mask", CVPixelBufferGetWidth(mask), CVPixelBufferGetHeight(mask))
