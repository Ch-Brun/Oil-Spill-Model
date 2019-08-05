from qgis.core import QgsProcessing
from qgis.core import QgsProcessingAlgorithm
from qgis.core import QgsProcessingMultiStepFeedback
from qgis.core import QgsProcessingParameterVectorLayer
from qgis.core import QgsProcessingParameterField
from qgis.core import QgsProcessingParameterNumber
from qgis.core import QgsProcessingParameterFeatureSink
import processing


class OilSpillModellingFirstStage(QgsProcessingAlgorithm):

    def initAlgorithm(self, config=None):
        self.addParameter(QgsProcessingParameterVectorLayer('coordeventx', 'Velocity x ', types=[QgsProcessing.TypeVectorPoint], defaultValue=None))
        self.addParameter(QgsProcessingParameterVectorLayer('coordeventy', 'Velocity y', types=[QgsProcessing.TypeVectorPoint], defaultValue=None))
        self.addParameter(QgsProcessingParameterField('date', 'Time after the spill in minutes', type=QgsProcessingParameterField.Any, parentLayerParameterName='coordeventx', allowMultiple=False, defaultValue=None))
        self.addParameter(QgsProcessingParameterVectorLayer('depthlayer', 'Depthlayer', types=[QgsProcessing.TypeVector], defaultValue=None))
        self.addParameter(QgsProcessingParameterVectorLayer('perimetercrude', 'Perimeter', types=[QgsProcessing.TypeVectorPolygon], defaultValue=None))
        self.addParameter(QgsProcessingParameterVectorLayer('sourcepoint2', 'Pouring point outside the building ', types=[QgsProcessing.TypeVectorPoint], defaultValue=None))
        self.addParameter(QgsProcessingParameterVectorLayer('tankpoint', 'Location of the heating oil tank', types=[QgsProcessing.TypeVectorPoint], defaultValue=None))
        self.addParameter(QgsProcessingParameterNumber('temperature', 'Temperature in °C', type=QgsProcessingParameterNumber.Double, minValue=-50, maxValue=50, defaultValue=13.74))
        self.addParameter(QgsProcessingParameterNumber('timespanbetweenstages', 'Timespan between stages', type=QgsProcessingParameterNumber.Double, minValue=1, maxValue=100, defaultValue=1))
        self.addParameter(QgsProcessingParameterNumber('volumen', 'Volume in litres', type=QgsProcessingParameterNumber.Double, minValue=1, maxValue=1e+06, defaultValue=2000))
        self.addParameter(QgsProcessingParameterFeatureSink('OutputFirstStageModell', 'Output first stage modell', type=QgsProcessing.TypeVectorAnyGeometry, createByDefault=True, defaultValue=None))
        self.addParameter(QgsProcessingParameterNumber('timemin', 'Time since spill in minutes (>=1)', type=QgsProcessingParameterNumber.Double, minValue=1, maxValue=1440, defaultValue=0))

    def processAlgorithm(self, parameters, context, model_feedback):
        # Use a multi-step feedback, so that individual child algorithm progress reports are adjusted for the
        # overall progress through the model
        feedback = QgsProcessingMultiStepFeedback(12, model_feedback)
        results = {}
        outputs = {}

        # Gitter (Nächster Nachbar)
        alg_params = {
            'ANGLE': 0,
            'DATA_TYPE': 5,
            'INPUT': parameters['depthlayer'],
            'NODATA': 0,
            'OPTIONS': '',
            'RADIUS_1': 0,
            'RADIUS_2': 0,
            'Z_FIELD': parameters['date'],
            'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT
        }
        outputs['GitterNchsterNachbar'] = processing.run('gdal:gridnearestneighbor', alg_params, context=context, feedback=feedback, is_child_algorithm=True)

        feedback.setCurrentStep(1)
        if feedback.isCanceled():
            return {}

        # Puffer
        alg_params = {
            'DISSOLVE': False,
            'DISTANCE': QgsProperty.fromExpression('((@volumen/1000 )*4/(pi()*3))^(1/3)'),
            'END_CAP_STYLE': 0,
            'INPUT': parameters['sourcepoint2'],
            'JOIN_STYLE': 0,
            'MITER_LIMIT': 2,
            'SEGMENTS': 10,
            'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT
        }
        outputs['Puffer'] = processing.run('native:buffer', alg_params, context=context, feedback=feedback, is_child_algorithm=True)

        feedback.setCurrentStep(2)
        if feedback.isCanceled():
            return {}

        # Zufällige Punkte in Polygonen
        alg_params = {
            'EXPRESSION': ' @volumen ',
            'INPUT': outputs['Puffer']['OUTPUT'],
            'MIN_DISTANCE': 0,
            'STRATEGY': 0,
            'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT
        }
        outputs['ZuflligePunkteInPolygonen'] = processing.run('qgis:randompointsinsidepolygons', alg_params, context=context, feedback=feedback, is_child_algorithm=True)

        feedback.setCurrentStep(3)
        if feedback.isCanceled():
            return {}

        # Gitter (Inverse Distanz zu einer Potenz)
        alg_params = {
            'ANGLE': 0,
            'DATA_TYPE': 5,
            'INPUT': parameters['coordeventy'],
            'MAX_POINTS': 0,
            'MIN_POINTS': 0,
            'NODATA': 0,
            'OPTIONS': '',
            'POWER': 2,
            'RADIUS_1': 0,
            'RADIUS_2': 0,
            'SMOOTHING': 0,
            'Z_FIELD': parameters['date'],
            'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT
        }
        outputs['GitterInverseDistanzZuEinerPotenz'] = processing.run('gdal:gridinversedistance', alg_params, context=context, feedback=feedback, is_child_algorithm=True)

        feedback.setCurrentStep(4)
        if feedback.isCanceled():
            return {}

        # Gitter (Inverse Distanz zu einer Potenz)
        alg_params = {
            'ANGLE': 0,
            'DATA_TYPE': 5,
            'INPUT': parameters['coordeventx'],
            'MAX_POINTS': 0,
            'MIN_POINTS': 0,
            'NODATA': 0,
            'OPTIONS': '',
            'POWER': 2,
            'RADIUS_1': 0,
            'RADIUS_2': 0,
            'SMOOTHING': 0,
            'Z_FIELD': parameters['date'],
            'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT
        }
        outputs['GitterInverseDistanzZuEinerPotenz'] = processing.run('gdal:gridinversedistance', alg_params, context=context, feedback=feedback, is_child_algorithm=True)

        feedback.setCurrentStep(5)
        if feedback.isCanceled():
            return {}

        # Felder überarbeiten
        alg_params = {
            'FIELDS_MAPPING': [{'expression': '"id"', 'length': 10, 'name': 'id', 'precision': 0, 'type': 4}],
            'INPUT': outputs['ZuflligePunkteInPolygonen']['OUTPUT'],
            'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT
        }
        outputs['FelderBerarbeiten'] = processing.run('qgis:refactorfields', alg_params, context=context, feedback=feedback, is_child_algorithm=True)

        feedback.setCurrentStep(6)
        if feedback.isCanceled():
            return {}

        # Add raster values to features
        alg_params = {
            'GRIDS': [outputs['GitterNchsterNachbar']['OUTPUT'],outputs['GitterInverseDistanzZuEinerPotenz']['OUTPUT'],outputs['GitterInverseDistanzZuEinerPotenz']['OUTPUT']],
            'RESAMPLING': 0,
            'SHAPES': parameters['perimetercrude'],
            'RESULT': QgsProcessing.TEMPORARY_OUTPUT
        }
        outputs['AddRasterValuesToFeatures'] = processing.run('saga:addrastervaluestofeatures', alg_params, context=context, feedback=feedback, is_child_algorithm=True)

        feedback.setCurrentStep(7)
        if feedback.isCanceled():
            return {}

        # Verschieben
        alg_params = {
            'DELTA_M': 0,
            'DELTA_X': QgsProperty.fromExpression('(sqrt((pi()*1.21^2*(((@volumen/1000)^2*9.81*0.1793*((1/60)* @timemin )^1.5)/0.000001139^0.5)^(1/3))/pi()))/60
* sin(azimuth( make_point( @tankpoint_minx ,  @tankpoint_miny), $geometry))*60* @timespanbetweenstages'),
            'DELTA_Y': QgsProperty.fromExpression('(sqrt((pi()*1.21^2*(((@volumen/1000)^2*9.81*0.1793*((1/60)* @timemin )^1.5)/0.000001139^0.5)^(1/3))/pi()))/60 * cos(azimuth( make_point( @tankpoint_minx ,  @tankpoint_miny), $geometry))*60* @timespanbetweenstages'),
            'DELTA_Z': 0,
            'INPUT': outputs['FelderBerarbeiten']['OUTPUT'],
            'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT
        }
        outputs['Verschieben'] = processing.run('native:translategeometry', alg_params, context=context, feedback=feedback, is_child_algorithm=True)

        feedback.setCurrentStep(8)
        if feedback.isCanceled():
            return {}

        # Zufällige Auswahl
        alg_params = {
            'INPUT': outputs['Verschieben']['OUTPUT'],
            'METHOD': 1,
            'NUMBER': QgsExpression('100- (floor( (5.91 + 0.045 *@temperature )*ln(@timemin)))').evaluate()
        }
        outputs['ZuflligeAuswahl'] = processing.run('qgis:randomselection', alg_params, context=context, feedback=feedback, is_child_algorithm=True)

        feedback.setCurrentStep(9)
        if feedback.isCanceled():
            return {}

        # Gewählte Objekte exportieren
        alg_params = {
            'INPUT': outputs['ZuflligeAuswahl']['OUTPUT'],
            'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT
        }
        outputs['GewhlteObjekteExportieren'] = processing.run('native:saveselectedfeatures', alg_params, context=context, feedback=feedback, is_child_algorithm=True)

        feedback.setCurrentStep(10)
        if feedback.isCanceled():
            return {}

        # Attribute nach Position zusammenfügen
        alg_params = {
            'DISCARD_NONMATCHING': True,
            'INPUT': outputs['GewhlteObjekteExportieren']['OUTPUT'],
            'JOIN': outputs['AddRasterValuesToFeatures']['RESULT'],
            'JOIN_FIELDS': None,
            'METHOD': 0,
            'PREDICATE': 0,
            'PREFIX': '',
            'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT
        }
        outputs['AttributeNachPositionZusammenfgen'] = processing.run('qgis:joinattributesbylocation', alg_params, context=context, feedback=feedback, is_child_algorithm=True)

        feedback.setCurrentStep(11)
        if feedback.isCanceled():
            return {}

        # Verschieben
        alg_params = {
            'DELTA_M': 0,
            'DELTA_X': QgsProperty.fromExpression('CASE 
WHEN "OUTPUT_2" > 0  
THEN "OUTPUT" * 60 *  @timespanbetweenstages 
ELSE 0
END'),
            'DELTA_Y': QgsProperty.fromExpression('CASE 
WHEN "OUTPUT_2" > 0 
THEN  "OUTPUT_1" * 60 *  @timespanbetweenstages 
ELSE 0
END'),
            'DELTA_Z': 0,
            'INPUT': outputs['AttributeNachPositionZusammenfgen']['OUTPUT'],
            'OUTPUT': parameters['OutputFirstStageModell']
        }
        outputs['Verschieben'] = processing.run('native:translategeometry', alg_params, context=context, feedback=feedback, is_child_algorithm=True)
        results['OutputFirstStageModell'] = outputs['Verschieben']['OUTPUT']
        return results

    def name(self):
        return '1oil spill modelling first stage'

    def displayName(self):
        return '1oil spill modelling first stage'

    def group(self):
        return ''

    def groupId(self):
        return ''

    def createInstance(self):
        return OilSpillModellingFirstStage()
