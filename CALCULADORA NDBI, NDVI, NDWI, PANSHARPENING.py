"""
Name : Pansharpen + NDVI/NDBI/NDWI
Group : Satellite Imagery
With QGIS : 33403
"""

from qgis.core import QgsProcessing, QgsProcessingAlgorithm, QgsProcessingMultiStepFeedback
from qgis.core import QgsProcessingParameterRasterLayer, QgsProcessingParameterRasterDestination
import processing
class PansharpenAndIndicesTool(QgsProcessingAlgorithm):
    def initAlgorithm(self, config=None):
        self.addParameter(QgsProcessingParameterRasterLayer('red', 'Red', defaultValue=None))
        self.addParameter(QgsProcessingParameterRasterLayer('green', 'Green', defaultValue=None))
        self.addParameter(QgsProcessingParameterRasterLayer('blue', 'Blue', defaultValue=None))
        self.addParameter(QgsProcessingParameterRasterLayer('panchromatic', 'Panchromatic', defaultValue=None))
        self.addParameter(QgsProcessingParameterRasterLayer('nir', 'NIR (Near Infrared)', defaultValue=None))
        self.addParameter(QgsProcessingParameterRasterLayer('swir', 'SWIR (Shortwave Infrared, SWIR1 preferido)', defaultValue=None))
        self.addParameter(QgsProcessingParameterRasterDestination('Pansharpened', 'Pansharpened', createByDefault=True, defaultValue=None))
        self.addParameter(QgsProcessingParameterRasterDestination('NDVI', 'NDVI', createByDefault=True, defaultValue=None))
        self.addParameter(QgsProcessingParameterRasterDestination('NDBI', 'NDBI', createByDefault=True, defaultValue=None))
        self.addParameter(QgsProcessingParameterRasterDestination('NDWI', 'NDWI (McFeeters: Green vs NIR)', createByDefault=True, defaultValue=None))
        self.addParameter(QgsProcessingParameterRasterDestination('NDWI_GAO', 'NDWI (Gao: NIR vs SWIR)', createByDefault=True, defaultValue=None))
    def processAlgorithm(self, parameters, context, model_feedback):
        feedback = QgsProcessingMultiStepFeedback(7, model_feedback)
        results, outputs = {}, {}
        alg_params = {
            'ADD_ALPHA': False,
            'ASSIGN_CRS': None,
            'EXTRA': '',
            'INPUT': [parameters['red'], parameters['green'], parameters['blue']],
            'PROJ_DIFFERENCE': False,
            'RESAMPLING': 0,   # Nearest neighbour
            'RESOLUTION': 0,   # Average
            'SEPARATE': True,
            'SRC_NODATA': '',
            'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT
        }
        outputs['VRT_RGB'] = processing.run(
            'gdal:buildvirtualraster', alg_params,
            context=context, feedback=feedback, is_child_algorithm=True
        )

        feedback.setCurrentStep(1)
        if feedback.isCanceled(): return results
        alg_params = {
            'EXTRA': '',
            'OPTIONS': '',
            'PANCHROMATIC': parameters['panchromatic'],
            'RESAMPLING': 2,  # Cubic (4x4)
            'SPECTRAL': outputs['VRT_RGB']['OUTPUT'],
            'OUTPUT': parameters['Pansharpened']
        }
        outputs['Pansharp'] = processing.run(
            'gdal:pansharp', alg_params,
            context=context, feedback=feedback, is_child_algorithm=True
        )
        results['Pansharpened'] = outputs['Pansharp']['OUTPUT']

        feedback.setCurrentStep(2)
        if feedback.isCanceled(): return results
        alg_params = {
            'ADD_ALPHA': False,
            'ASSIGN_CRS': None,
            'EXTRA': '',
            'INPUT': [parameters['nir'], parameters['red'], parameters['swir'], parameters['green']],
            'PROJ_DIFFERENCE': False,
            'RESAMPLING': 2,   # Cubic para reflectancias
            'RESOLUTION': 1,   # Highest (máxima resolución de las entradas)
            'SEPARATE': True,
            'SRC_NODATA': '',
            'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT
        }
        outputs['VRT_STACK'] = processing.run(
            'gdal:buildvirtualraster', alg_params,
            context=context, feedback=feedback, is_child_algorithm=True
        )

        feedback.setCurrentStep(3)
        if feedback.isCanceled(): return results

        alg_params = {
            'INPUT_A': outputs['VRT_STACK']['OUTPUT'], 'BAND_A': 1,  # NIR
            'INPUT_B': outputs['VRT_STACK']['OUTPUT'], 'BAND_B': 2,  # RED
            'FORMULA': '(A - B) / (A + B + 1e-6)',
            'NO_DATA': -9999,
            'RTYPE': 5,  # Float32
            'OPTIONS': '',
            'EXTRA': '',
            'OUTPUT': parameters['NDVI']
        }
        outputs['NDVI'] = processing.run(
            'gdal:rastercalculator', alg_params,
            context=context, feedback=feedback, is_child_algorithm=True
        )
        results['NDVI'] = outputs['NDVI']['OUTPUT']

        feedback.setCurrentStep(4)
        if feedback.isCanceled(): return results

        alg_params = {
            'INPUT_A': outputs['VRT_STACK']['OUTPUT'], 'BAND_A': 3,  # SWIR
            'INPUT_B': outputs['VRT_STACK']['OUTPUT'], 'BAND_B': 1,  # NIR
            'FORMULA': '(A - B) / (A + B + 1e-6)',
            'NO_DATA': -9999,
            'RTYPE': 5,
            'OPTIONS': '',
            'EXTRA': '',
            'OUTPUT': parameters['NDBI']
        }
        outputs['NDBI'] = processing.run(
            'gdal:rastercalculator', alg_params,
            context=context, feedback=feedback, is_child_algorithm=True
        )
        results['NDBI'] = outputs['NDBI']['OUTPUT']

        feedback.setCurrentStep(5)
        if feedback.isCanceled(): return results
        
        alg_params = {
            'INPUT_A': outputs['VRT_STACK']['OUTPUT'], 'BAND_A': 4,  # GREEN
            'INPUT_B': outputs['VRT_STACK']['OUTPUT'], 'BAND_B': 1,  # NIR
            'FORMULA': '(A - B) / (A + B + 1e-6)',
            'NO_DATA': -9999,
            'RTYPE': 5,
            'OPTIONS': '',
            'EXTRA': '',
            'OUTPUT': parameters['NDWI']
        }
        outputs['NDWI'] = processing.run(
            'gdal:rastercalculator', alg_params,
            context=context, feedback=feedback, is_child_algorithm=True
        )
        results['NDWI'] = outputs['NDWI']['OUTPUT']

        feedback.setCurrentStep(6)
        if feedback.isCanceled(): return results
        alg_params = {
            'INPUT_A': outputs['VRT_STACK']['OUTPUT'], 'BAND_A': 1,  # NIR
            'INPUT_B': outputs['VRT_STACK']['OUTPUT'], 'BAND_B': 3,  # SWIR
            'FORMULA': '(A - B) / (A + B + 1e-6)',
            'NO_DATA': -9999,
            'RTYPE': 5,
            'OPTIONS': '',
            'EXTRA': '',
            'OUTPUT': parameters['NDWI_GAO']
        }
        outputs['NDWI_GAO'] = processing.run(
            'gdal:rastercalculator', alg_params,
            context=context, feedback=feedback, is_child_algorithm=True
        )
        results['NDWI_GAO'] = outputs['NDWI_GAO']['OUTPUT']
        return results
    def name(self):
        return 'PansharpenAndIndices'
    def displayName(self):
        return 'Pansharpen + NDVI/NDBI/NDWI'
    def group(self):
        return 'Satellite Imagery'
    def groupId(self):
        return 'Satellite Imagery'
    def shortHelpString(self):
        return """<html><body>
        <p>Realiza pansharpening y calcula NDVI, NDBI y NDWI (McFeeters y Gao).</p>
        <h3>Entradas</h3>
        <ul>
          <li><b>Red/Green/Blue</b>: bandas monocanal.</li>
          <li><b>Panchromatic</b>: banda PAN de mayor resolución.</li>
          <li><b>NIR</b> y <b>SWIR</b> (SWIR1 preferible).</li>
        </ul>
        <h3>Notas</h3>
        <ul>
          <li>Las fórmulas usan un epsilon (1e-6) para evitar división por cero.</li>
          <li>El VRT de índices utiliza <i>RESOLUTION = Highest</i> y <i>RESAMPLING = Cubic</i> para alinear entradas.</li>
          <li><b>Landsat 8/9</b> típico: R=B4, G=B3, B=B2, PAN=B8, NIR=B5, SWIR=B6.</li>
          <li><b>Sentinel-2</b> típico: R=B4 (10 m), G=B3 (10 m), B=B2 (10 m), NIR=B8 (10 m), SWIR=B11 (20 m).</li>
        </ul>
        <p align="right">Juanesteban Mariño.</p>
        </body></html>"""

    def createInstance(self):
        return PansharpenAndIndicesTool()
